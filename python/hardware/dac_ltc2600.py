# ============================================================
# hardware/dac_ltc2600.py — LTC2600 5× daisy-chain driver
#
# Identical logic to LTCgood.py (confirmed working).
# Pins and voltage range come from config.py LTC2600_* constants.
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import nidaqmx
from nidaqmx.constants import LineGrouping
from config import (
    DEVICE,
    DAC_NUM_DACS, DAC_NUM_CH, DAC_BITS,
    LTC2600_PIN_CLR, LTC2600_PIN_SDI, LTC2600_PIN_SCK, LTC2600_PIN_CS,
    LTC2600_VMIN, LTC2600_VMAX, LTC2600_VREF,
)

PORT     = "port0"
IDX_CLRn = LTC2600_PIN_CLR
IDX_SDI  = LTC2600_PIN_SDI
IDX_SCK  = LTC2600_PIN_SCK
IDX_CSn  = LTC2600_PIN_CS
NUM_DACS = DAC_NUM_DACS
NUM_CH   = DAC_NUM_CH
BITS     = DAC_BITS
VMIN     = LTC2600_VMIN
VMAX     = LTC2600_VMAX
VREF     = LTC2600_VREF

DELAY = 1e-4   # 100 µs per phase — matches LTCgood.py

_LO = min(IDX_CLRn, IDX_SDI, IDX_SCK, IDX_CSn)   # 0
_HI = max(IDX_CLRn, IDX_SDI, IDX_SCK, IDX_CSn)   # 3

_IDLE = (1 << IDX_CLRn) | (1 << IDX_CSn)   # CLRn=H, CSn=H

_state = [[0.0] * NUM_CH for _ in range(NUM_DACS)]


# ── SPI bus ───────────────────────────────────────────────────
# Persistent task opened at module level — same pattern as LTCgood.py.
# Task and state word kept alive so every SetDigitalOutput call
# modifies one bit and pushes the whole word (one USB transaction).

class _Bus:
    def __init__(self):
        self._task  = None
        self._state = _IDLE

    def open(self):
        self._task = nidaqmx.Task()
        self._task.do_channels.add_do_chan(
            f"{DEVICE}/{PORT}/line{_LO}:{_HI}",
            line_grouping=LineGrouping.CHAN_FOR_ALL_LINES,
        )
        self._task.start()
        self._push()

    def _push(self):
        self._task.write(self._state)

    def set(self, line_idx: int, value: bool):
        if value: self._state |=  (1 << line_idx)
        else:     self._state &= ~(1 << line_idx)
        self._push()

    def restore(self):
        self._state = _IDLE
        self._push()

    def close(self):
        try:
            self.restore()
            self._task.stop()
            self._task.close()
        except Exception:
            pass


_bus = _Bus()


def _open_bus():
    """Open the persistent bus on first use."""
    if _bus._task is None:
        _bus.open()


# ── Frame builder — identical to LTCgood._build_sdi_string ───

def _build_sdi(dac_num: int, channel: int, code: int) -> str:
    cmd_byte = 0x30 + (channel - 1)
    active   = format(cmd_byte & 0xFFFF, '016b') + format(code, '016b')
    noop     = format(0xFF, '016b') + format(0x0000, '016b')
    post_buf = NUM_DACS - dac_num
    pre_buf  = dac_num - 1
    sdi = noop * post_buf + active + noop * pre_buf
    assert len(sdi) == NUM_DACS * 32
    return sdi


# ── Serial send — identical to LTCgood.send_serial_dac_data ──

def _send(sdi_string: str):
    _bus.set(IDX_CSn, False)        # CSn LOW
    time.sleep(DELAY)

    j = 0
    for c in range(1, NUM_DACS * 64 + 3):   # 322 for 5 DACs
        if c <= NUM_DACS * 64:
            if c % 2 == 1:                   # odd: SCK LOW + set SDI
                bit = int(sdi_string[j]); j += 1
                _bus.set(IDX_SCK, False); time.sleep(DELAY)
                _bus.set(IDX_SDI, bool(bit)); time.sleep(DELAY)
            else:                            # even: SCK HIGH (rising edge → latch)
                _bus.set(IDX_SCK, True); time.sleep(DELAY)
        elif c == NUM_DACS * 64 + 1:
            _bus.set(IDX_CSn, True);  time.sleep(DELAY)   # CSn HIGH → latch
            _bus.set(IDX_SCK, False); time.sleep(DELAY)
        elif c == NUM_DACS * 64 + 2:
            _bus.set(IDX_SCK, True);  time.sleep(DELAY)   # extra pulse


# ── Public API ────────────────────────────────────────────────

def initialize(device=DEVICE) -> bool:
    global _state
    _state = [[0.0]*NUM_CH for _ in range(NUM_DACS)]
    _open_bus()
    print("="*50); print("  LTC2600 Initialization"); print("="*50)

    print("Hardware Clear...", end="", flush=True)
    _bus.set(IDX_CSn,  True)
    _bus.set(IDX_CLRn, True);  time.sleep(0.001)
    _bus.set(IDX_CLRn, False); time.sleep(0.005)
    _bus.set(IDX_CLRn, True);  time.sleep(0.005)
    print(" Done")

    print(f"\n=== LTC2600 Ready — {VMIN}V to {VMAX}V (VREF={VREF}V) ===\n")
    return True


def set_voltage(dac_num: int, ch_num: int, voltage: float, device=DEVICE) -> bool:
    global _state
    if not (1 <= dac_num <= NUM_DACS): print(f"ERROR: dac_num 1-{NUM_DACS}"); return False
    if not (1 <= ch_num  <= NUM_CH):   print(f"ERROR: ch_num 1-{NUM_CH}");    return False

    _open_bus()
    voltage = max(VMIN, min(float(voltage), VMAX))
    code    = int(round((voltage / VREF) * 0xFFFF))
    code    = max(0, min(code, 0xFFFF))

    sdi = _build_sdi(dac_num, ch_num, code)
    _send(sdi)

    _state[dac_num-1][ch_num-1] = voltage
    print(f"DAC{dac_num} CH{ch_num} = {voltage:.4f}V  (0x{code:04X})")
    return True


def clear_all(num_dacs=NUM_DACS, device=DEVICE) -> None:
    global _state
    _open_bus()
    _bus.set(IDX_CLRn, False); time.sleep(0.005)
    _bus.set(IDX_CLRn, True);  time.sleep(0.005)
    _state = [[0.0]*NUM_CH for _ in range(NUM_DACS)]
    print("All DACs cleared to 0V via CLR.")


def get_voltage(dac_num: int, ch_num: int) -> float:
    return _state[dac_num-1][ch_num-1]


def print_state() -> None:
    print("\n── LTC2600 State (V) " + "─"*31)
    print("     " + "".join(f"  DAC{d+1}" for d in range(NUM_DACS)))
    for ch in range(NUM_CH):
        print(f"CH{ch+1:2d} " + "".join(f"  {_state[d][ch]:5.3f}" for d in range(NUM_DACS)))
    print("─"*51 + "\n")


def cleanup():
    _bus.close()