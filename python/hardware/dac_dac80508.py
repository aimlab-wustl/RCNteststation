# ============================================================
# hardware/dac_dac80508.py — DAC80508 5× daisy-chain driver
#
# TI DAC80508: octal 16-bit DAC, internal 2.5 V reference, SPI.
# 5× devices daisy-chained on NI USB-6212 port0 DIO lines.
#
# NI USB-6212 DIO is software-timed (OnDemand) only.
# The persistent-task pattern keeps the NI task open across all
# writes inside an initialize()/set_voltage() sequence, avoiding
# the per-call task open/close overhead of earlier versions.
#
# Pins (edit DAC80508_PIN_* in config.py):
#   port0/line1 → SDI
#   port0/line2 → SCK
#   port0/line3 → CSn
#
# Public API (mirrors dac_ad5676r.py):
#   initialize()               reset + configure all 5 DACs
#   set_voltage(d, ch, v)      write one channel on one DAC
#   clear_all()                zero all 40 outputs
#   get_voltage(d, ch)         return last commanded voltage
#   print_state()              print 5×8 voltage table
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import nidaqmx
from nidaqmx.constants import LineGrouping
from config import (
    DEVICE,
    DAC_NUM_DACS, DAC_NUM_CH, DAC_BITS,
    DAC80508_PIN_SDI, DAC80508_PIN_SCK, DAC80508_PIN_CSN,
    DAC80508_VMIN, DAC80508_VMAX,
)

# ── Module constants ──────────────────────────────────────────
PORT     = "port0"
PIN_SDI  = DAC80508_PIN_SDI
PIN_SCK  = DAC80508_PIN_SCK
PIN_CSN  = DAC80508_PIN_CSN
NUM_DACS = DAC_NUM_DACS
NUM_CH   = DAC_NUM_CH
BITS     = DAC_BITS
VMIN     = DAC80508_VMIN
VMAX     = DAC80508_VMAX

# DAC80508 register addresses
_REG_NOP     = 0x00
_REG_SYNC    = 0x02
_REG_CONFIG  = 0x03
_REG_GAIN    = 0x04
_REG_TRIGGER = 0x05
_REG_DAC0    = 0x08   # DAC0..DAC7 → 0x08..0x0F
_CONFIG_INTERNAL_REF = 0x0000   # internal ref enabled (default)
_CONFIG_EXTERNAL_REF = 0x0100   # REF-PWDWN=1: disable internal ref, use external

# gain=2, REFDIV disabled → 2.5 V ref (internal or external) × 2 = 5 V full scale
_GAIN_REG_5V = 0x00FF

# Module-level state: last commanded voltage per [dac][ch]
_state = [[0.0] * NUM_CH for _ in range(NUM_DACS)]

# Persistent bus instance — opened by initialize(), closed by clear_all()
# or when the process exits.  set_voltage() reuses it.
_bus = None


# ════════════════════════════════════════════════════════════════
# Internal: low-level bus
# ════════════════════════════════════════════════════════════════

class _Bus:
    """
    Software-timed SPI bit-bang on NI USB-6212 OnDemand DO.
    Task stays open for the lifetime of the object; each bus state
    is one task.write() call.
    """

    def __init__(self, device=DEVICE):
        self._task   = None
        self._device = device

    def open(self):
        self._task = nidaqmx.Task()
        for pin in (PIN_SDI, PIN_SCK, PIN_CSN):
            self._task.do_channels.add_do_chan(
                f"{self._device}/{PORT}/line{pin}",
                line_grouping=LineGrouping.CHAN_PER_LINE,
            )
        self._task.start()
        self._wr(False, False, True)   # idle: SDI=0 SCK=0 CSn=1

    def close(self):
        if self._task is not None:
            try:
                self._wr(False, False, True)
                self._task.stop()
                self._task.close()
            except Exception:
                pass
            self._task = None

    def _wr(self, sdi, sck, csn):
        self._task.write([bool(sdi), bool(sck), bool(csn)], auto_start=False)

    def send(self, chain_int, n_bits):
        """Clock out one SPI transaction. DAC80508 latches on SCK falling edge."""
        # Assert CSn
        self._wr(False, False, False)

        for k in range(n_bits):
            bit = bool((chain_int >> (n_bits - 1 - k)) & 1)
            self._wr(bit, True,  False)   # SDI valid, SCK high
            self._wr(bit, False, False)   # SCK falling edge → DAC latches

        # Deassert CSn: rising edge transfers shift register to output register
        self._wr(False, False, True)


# ════════════════════════════════════════════════════════════════
# Internal: frame / chain builders  (pure, no I/O)
# ════════════════════════════════════════════════════════════════

_FRAME_BITS = NUM_DACS * 24   # 120 bits total for 5-device chain

def _frame(addr, data):
    """24-bit write word: R/W=0, addr[3:0], data[15:0]."""
    return ((addr & 0x0F) << 16) | (data & 0xFFFF)

def _nop():
    return _frame(_REG_NOP, 0)

def _chain_one(dac_num, addr, data):
    """
    120-bit chain word: real frame for dac_num, NOPs for the rest.
    DAC1 is closest to SDI; DAC5 is farthest → DAC5 word clocked first.
    """
    words = [_nop()] * NUM_DACS
    words[dac_num - 1] = _frame(addr, data)
    result = 0
    for i in range(NUM_DACS - 1, -1, -1):
        result = (result << 24) | words[i]
    return result

def _chain_all_same(addr, data):
    """120-bit chain word: same register/data to every DAC."""
    w = _frame(addr, data)
    result = 0
    for _ in range(NUM_DACS):
        result = (result << 24) | w
    return result

def _chain_all_data(addr, data_by_dac):
    """120-bit chain word: same register, individual data per DAC."""
    result = 0
    for i in range(NUM_DACS - 1, -1, -1):
        result = (result << 24) | _frame(addr, int(data_by_dac[i]) & 0xFFFF)
    return result


# ════════════════════════════════════════════════════════════════
# Internal: voltage helpers
# ════════════════════════════════════════════════════════════════

def _clamp(v):
    return max(VMIN, min(float(v), VMAX))

def _to_code(v):
    return int(round((_clamp(v) / VMAX) * ((1 << BITS) - 1)))

def _validate_dac(n):
    if not (1 <= n <= NUM_DACS):
        raise ValueError(f"dac_num must be 1..{NUM_DACS}")

def _validate_ch(n):
    if not (1 <= n <= NUM_CH):
        raise ValueError(f"ch_num must be 1..{NUM_CH}")


# ════════════════════════════════════════════════════════════════
# Internal: send helpers (require _bus to be open)
# ════════════════════════════════════════════════════════════════

def _send_one(dac_num, addr, data):
    _bus.send(_chain_one(dac_num, addr, data), _FRAME_BITS)

def _send_all_same(addr, data):
    _bus.send(_chain_all_same(addr, data), _FRAME_BITS)

def _send_all_data(addr, data_by_dac):
    _bus.send(_chain_all_data(addr, data_by_dac), _FRAME_BITS)


# ════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════

def initialize(device=DEVICE, use_external_ref=False) -> bool:
    """
    Open the NI task, reset all 5 DAC80508s, and configure for 0–5 V.
    Must be called once before set_voltage().

    Args:
        device:            NI DAQ device string (default from config.py)
        use_external_ref:  True  → disable internal 2.5 V reference; REF pin
                                   becomes an input. Connect your external 2.5 V
                                   ref to REF before calling initialize().
                           False → use internal 2.5 V reference (default).
    """
    global _bus, _state

    if _bus is not None:
        _bus.close()

    _bus = _Bus(device=device)
    _bus.open()

    _state = [[0.0] * NUM_CH for _ in range(NUM_DACS)]

    print("=" * 50)
    print("  DAC80508 Initialization")
    print("=" * 50)

    print("Software reset...", end="", flush=True)
    _send_all_same(_REG_TRIGGER, 0x000A)
    time.sleep(0.02)
    print(" Done")

    ref_config = _CONFIG_EXTERNAL_REF if use_external_ref else _CONFIG_INTERNAL_REF
    ref_label  = "external" if use_external_ref else "internal"

    print(f"Configuring reference ({ref_label})...", end="", flush=True)
    _send_all_same(_REG_CONFIG, ref_config)
    time.sleep(0.002)
    print(" Done")

    print("Setting async update mode...", end="", flush=True)
    _send_all_same(_REG_SYNC, 0x0000)
    time.sleep(0.002)
    print(" Done")

    print("Setting gain=2 (0–5 V range)...", end="", flush=True)
    _send_all_same(_REG_GAIN, _GAIN_REG_5V)
    time.sleep(0.002)
    print(" Done")

    _clear_outputs()

    ref_note = ("REF pin is now an input — ensure external 2.5 V ref is connected."
                if use_external_ref else
                "REF pin should read ~2.5 V.")
    print(f"\n=== DAC80508 Ready — {VMIN:.1f} V to {VMAX:.1f} V, {BITS}-bit ===")
    print(ref_note + "\n")
    return True


def set_voltage(dac_num: int, ch_num: int, voltage: float,
                device=DEVICE) -> bool:
    """
    Set one channel on one DAC.

    Args:
        dac_num:  1–5
        ch_num:   1–8  (1 = OUT0, 8 = OUT7)
        voltage:  0–5 V (clamped silently)
        device:   ignored if initialize() already called; kept for API parity

    Returns:
        True on success.
    """
    global _bus, _state

    if _bus is None:
        initialize(device=device)

    _validate_dac(dac_num)
    _validate_ch(ch_num)

    v    = _clamp(voltage)
    code = _to_code(v)
    reg  = _REG_DAC0 + (ch_num - 1)

    _send_one(dac_num, reg, code)
    _state[dac_num - 1][ch_num - 1] = v

    print(f"DAC{dac_num} CH{ch_num}/OUT{ch_num-1} = {v:.4f} V  (0x{code:04X})")
    return True


def clear_all(device=DEVICE) -> None:
    """Zero all 40 outputs and close the NI task."""
    global _bus, _state

    if _bus is not None:
        _clear_outputs()
        _bus.close()
        _bus = None

    _state = [[0.0] * NUM_CH for _ in range(NUM_DACS)]
    print("All DAC80508 outputs set to 0 V.")


def get_voltage(dac_num: int, ch_num: int) -> float:
    """Return the last voltage commanded to dac_num / ch_num."""
    return _state[dac_num - 1][ch_num - 1]


def print_state() -> None:
    """Print the 5×8 last-commanded voltage table."""
    print("\n── DAC80508 State (V) " + "─" * 29)
    print("     " + "".join(f"  DAC{d+1}" for d in range(NUM_DACS)))
    for ch in range(NUM_CH):
        print(f"CH{ch+1:2d} " +
              "".join(f"  {_state[d][ch]:5.3f}" for d in range(NUM_DACS)))
    print("─" * 51 + "\n")


# ════════════════════════════════════════════════════════════════
# Internal: clear helper (bus must already be open)
# ════════════════════════════════════════════════════════════════

def _clear_outputs() -> None:
    """Write 0x0000 to every DAC output register. Bus must be open."""
    code = 0x0000
    for ch_idx in range(NUM_CH):
        _send_all_same(_REG_DAC0 + ch_idx, code)


# ════════════════════════════════════════════════════════════════
# Quick self-test
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    initialize()
    set_voltage(1, 1, 2.0)
    set_voltage(2, 1, 4.0)
    set_voltage(3, 2, 2.5)
    set_voltage(4, 1, 4.0)
    set_voltage(5, 1, 0.0)
    print_state()
    input("\nMeasure outputs, then press Enter to clear and exit...")
    clear_all()