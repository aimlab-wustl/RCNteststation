# ============================================================
# hardware/dac_ad5676r.py — AD5676R 5× daisy-chain driver
#
# Two modes:
#   set_voltage()    — software-timed SPI,  ~4 Hz per update
#   generate_sine()  — hardware-timed DO buffer, ~10–80 Hz sine
#
# Pins (edit AD5676R_PIN_* in config.py):
#   port0/line1→RESET  port0/line2→SDI
#   port0/line3→SCK    port0/line4→SYNC
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import numpy as np
import nidaqmx
from nidaqmx.constants import LineGrouping, AcquisitionType
from config import (
    DEVICE,
    DAC_NUM_DACS, DAC_NUM_CH, DAC_BITS,
    AD5676R_PIN_RESET, AD5676R_PIN_SDI, AD5676R_PIN_SCK, AD5676R_PIN_SYNC,
    AD5676R_VMIN, AD5676R_VMAX,
)

PORT      = "port0"
PIN_RESET = AD5676R_PIN_RESET
PIN_SDI   = AD5676R_PIN_SDI
PIN_SCK   = AD5676R_PIN_SCK
PIN_SYNC  = AD5676R_PIN_SYNC
NUM_DACS  = DAC_NUM_DACS
NUM_CH    = DAC_NUM_CH
BITS      = DAC_BITS
VMIN      = AD5676R_VMIN
VMAX      = AD5676R_VMAX
VSPAN     = VMAX - VMIN

_LO = min(PIN_RESET, PIN_SDI, PIN_SCK, PIN_SYNC)
_HI = max(PIN_RESET, PIN_SDI, PIN_SCK, PIN_SYNC)

_B_RESET = PIN_RESET - _LO   # 0
_B_SDI   = PIN_SDI   - _LO   # 1
_B_SCK   = PIN_SCK   - _LO   # 2
_B_SYNC  = PIN_SYNC  - _LO   # 3

_IDLE      = (1 << _B_RESET) | (1 << _B_SYNC)
_state     = [[0.0] * NUM_CH for _ in range(NUM_DACS)]
_sine_task = None


# ══════════════════════════════════════════════════════════════
# Software-timed SPI bus  (initialize / set_voltage)
# ══════════════════════════════════════════════════════════════

class _Bus:
    def __init__(self):
        self._task = None
        self._w    = _IDLE

    def __enter__(self):
        self._task = nidaqmx.Task()
        self._task.do_channels.add_do_chan(
            f"{DEVICE}/{PORT}/line{_LO}:{_HI}",
            line_grouping=LineGrouping.CHAN_FOR_ALL_LINES,
        )
        self._wr(_IDLE)
        return self

    def __exit__(self, *_):
        try:
            self._wr(_IDLE)
            self._task.stop()
            self._task.close()
        except Exception:
            pass

    def _wr(self, w):
        self._w = w
        self._task.write(w)

    def set_reset(self, high: bool):
        w = self._w | (1<<_B_RESET) if high else self._w & ~(1<<_B_RESET)
        self._wr(w)

    def send_bits(self, bit_string: str):
        sdi = 1 << _B_SDI
        sck = 1 << _B_SCK
        syn = 1 << _B_SYNC
        w = self._w & ~syn;  self._wr(w)        # SYNC LOW
        for ch in bit_string:
            if ch == '1': w |=  sdi
            else:         w &= ~sdi
            w |= sck;  self._wr(w)              # SCK HIGH ← latch
            w &= ~sck; self._wr(w)              # SCK LOW
        w |= syn; self._wr(w)                   # SYNC HIGH
        self._w = w


# ══════════════════════════════════════════════════════════════
# Frame / chain helpers
# ══════════════════════════════════════════════════════════════

def _frame(cmd, addr, data) -> str:
    return format(((cmd&0xF)<<20)|((addr&0xF)<<16)|(data&0xFFFF), '024b')

def _chain(cmds, addrs, datas, n) -> str:
    return ''.join(_frame(cmds[i], addrs[i], datas[i]) for i in range(n-1,-1,-1))

def _send(bus, cmd, addr, data):   bus.send_bits(_frame(cmd, addr, data))
def _send_chain(bus, c, a, d, n): bus.send_bits(_chain(c, a, d, n))

def _clear_all(bus, n):
    for di in range(n):
        for ch in range(NUM_CH):
            c=[0xF]*n; c[di]=0x3
            a=[0x0]*n; a[di]=ch
            d=[0x0]*n
            _send_chain(bus, c, a, d, n)


# ══════════════════════════════════════════════════════════════
# Fast path: bit string → port word list
# One call per voltage step; all words sent in a single write()
# ══════════════════════════════════════════════════════════════

def _bits_to_words(bit_string: str) -> list:
    """
    Convert a SPI bit string into the exact list of packed port integers
    that send_bits() would write — same states, same order — but returned
    as a Python list instead of written one-by-one over USB.

    The resulting list is concatenated across all sine steps and loaded
    into a hardware-timed DO task in one USB transfer.
    """
    words = []
    sdi = 1 << _B_SDI
    sck = 1 << _B_SCK
    syn = 1 << _B_SYNC
    w   = _IDLE

    w = w & ~syn;   words.append(w)     # SYNC LOW
    for ch in bit_string:
        if ch == '1': w |=  sdi
        else:         w &= ~sdi
        w |= sck;  words.append(w)      # SCK HIGH
        w &= ~sck; words.append(w)      # SCK LOW
    w |= syn; words.append(w)           # SYNC HIGH
    return words


# ══════════════════════════════════════════════════════════════
# Public: initialize
# ══════════════════════════════════════════════════════════════

def initialize(device=DEVICE) -> bool:
    global _state
    _state = [[0.0]*NUM_CH for _ in range(NUM_DACS)]
    print("="*50); print("  AD5676R Initialization"); print("="*50)

    with _Bus() as bus:
        bus.set_reset(True)

        print("Hardware Reset...", end="", flush=True)
        bus.set_reset(False); time.sleep(0.02)
        bus.set_reset(True);  time.sleep(0.02)
        print(" Done")

        print("Software Reset...", end="", flush=True)
        _send(bus, 0x6, 0x0, 0x1234); time.sleep(0.1)
        print(" Done")

        print("Enabling DAC1...", end="", flush=True)
        _send(bus, 0x8, 0x0, 0x0001)
        _clear_all(bus, 1); time.sleep(0.5); print(" Done")

        print("Enabling DAC2...", end="", flush=True)
        _send_chain(bus,[0xF,0x8],[0,0],[0,0x0001],2)
        _clear_all(bus, 2); time.sleep(0.5); print(" Done")

        for n, label in [(3,"DAC3"),(4,"DAC4"),(5,"DAC5")]:
            print(f"Enabling {label}...", end="", flush=True)
            _send_chain(bus,[0xF]*(n-1)+[0x7],[0]*n,[0]*(n-1)+[0x0004],n); time.sleep(0.2)
            _send_chain(bus,[0xF]*(n-1)+[0x8],[0]*n,[0]*(n-1)+[0x0001],n); time.sleep(0.1)
            _clear_all(bus, n); time.sleep(0.5); print(" Done")

    print(f"\n=== AD5676R Ready — {VMIN}V to {VMAX}V, {BITS}-bit ===\n")
    return True


# ══════════════════════════════════════════════════════════════
# Public: set_voltage  (~4 Hz, software-timed)
# ══════════════════════════════════════════════════════════════

def set_voltage(dac_num: int, ch_num: int, voltage: float, device=DEVICE) -> bool:
    global _state
    if not (1 <= dac_num <= NUM_DACS): print(f"ERROR: dac_num 1-{NUM_DACS}"); return False
    if not (1 <= ch_num  <= NUM_CH):   print(f"ERROR: ch_num 1-{NUM_CH}");    return False
    voltage = max(VMIN, min(float(voltage), VMAX))
    code    = max(0, min(int((voltage/VSPAN)*((2**BITS)-1)), 0xFFFF))
    di, ci  = dac_num-1, ch_num-1
    cmds=[0xF]*NUM_DACS; cmds[di]=0x3
    addrs=[0x0]*NUM_DACS; addrs[di]=ci
    datas=[0x0]*NUM_DACS; datas[di]=code
    with _Bus() as bus:
        _send_chain(bus, cmds, addrs, datas, NUM_DACS)
    _state[di][ci] = voltage
    print(f"DAC{dac_num} CH{ch_num} = {voltage:.4f}V  (0x{code:04X})")
    return True


# ══════════════════════════════════════════════════════════════
# Public: generate_sine  (hardware-timed DO buffer)
# ══════════════════════════════════════════════════════════════

def generate_sine(
    dac_num:     int,
    ch_num:      int,
    frequency:   float,
    amplitude:   float,
    offset:      float = 2.5,
    sample_rate: int   = 200_000,
    device:      str   = DEVICE,
) -> nidaqmx.Task:
    """
    Output a sine wave on one DAC channel using the NI hardware DO buffer.

    Instead of calling set_voltage() in a Python loop (slow, USB-limited),
    this pre-computes the complete SPI bit sequence for every voltage step
    of the sine, packs all of it into one word array, and loads it into
    a hardware-timed DO task.  The NI hardware clocks the words out at
    sample_rate Hz with no further CPU or USB involvement.

    Speed:
        Words per voltage update = 242  (5×24 bits × 2 writes + 2 SYNC)
        Max update rate at 200 kS/s    = 200 000 / 242 ≈ 826 Hz
        Achievable sine with 20 pts    ≈ 41 Hz
        Achievable sine with 10 pts    ≈ 82 Hz

    Args:
        dac_num:     1–5
        ch_num:      1–8
        frequency:   Hz
        amplitude:   V peak (zero-to-peak)
        offset:      V DC offset (default 2.5 = mid-rail)
        sample_rate: NI DO hardware clock Hz (max ~250 000 on USB-6212)
        device:      NI DAQ device name

    Returns:
        Running nidaqmx.Task — call stop_sine() when done.

    Example:
        task = generate_sine(1, 1, frequency=10, amplitude=2.0, offset=2.5)
        time.sleep(30)
        stop_sine()
    """
    global _sine_task
    stop_sine()

    if not (1 <= dac_num <= NUM_DACS): raise ValueError(f"dac_num 1-{NUM_DACS}")
    if not (1 <= ch_num  <= NUM_CH):   raise ValueError(f"ch_num 1-{NUM_CH}")

    # Clamp to DAC range
    v_peak   = min(offset + amplitude, VMAX)
    v_trough = max(offset - amplitude, VMIN)
    act_amp  = (v_peak - v_trough) / 2
    act_off  = (v_peak + v_trough) / 2

    # Words per SPI transaction (5 DACs × 24 bits × 2 writes + 2 SYNC)
    words_per_step = 1 + (24 * NUM_DACS * 2) + 1   # 242

    # Points per cycle: enough for waveform shape, not too many
    max_update_hz  = sample_rate / words_per_step
    pts_per_cycle  = max(8, int(max_update_hz / frequency))
    pts_per_cycle  = min(pts_per_cycle, 500)        # cap buffer size

    actual_freq    = max_update_hz / pts_per_cycle

    print(f"[sine] Building buffer: {pts_per_cycle} pts/cycle × "
          f"{words_per_step} words = "
          f"{pts_per_cycle * words_per_step} total words")
    print(f"[sine] Actual frequency: {actual_freq:.2f} Hz  "
          f"(requested {frequency:.2f} Hz)")

    # Build voltage steps
    t         = np.linspace(0, 2*np.pi, pts_per_cycle, endpoint=False)
    voltages  = np.clip(act_off + act_amp * np.sin(t), VMIN, VMAX)

    # Build full word sequence
    di, ci    = dac_num-1, ch_num-1
    all_words = []

    for v in voltages:
        code = max(0, min(int((v/VSPAN)*((2**BITS)-1)), 0xFFFF))
        cmds=[0xF]*NUM_DACS; cmds[di]=0x3
        addrs=[0x0]*NUM_DACS; addrs[di]=ci
        datas=[0x0]*NUM_DACS; datas[di]=code
        all_words.extend(_bits_to_words(_chain(cmds, addrs, datas, NUM_DACS)))

    total_samples = len(all_words)

    # Load into hardware-timed DO task
    task = nidaqmx.Task()
    task.do_channels.add_do_chan(
        f"{device}/{PORT}/line{_LO}:{_HI}",
        line_grouping=LineGrouping.CHAN_FOR_ALL_LINES,
    )
    task.timing.cfg_samp_clk_timing(
        rate           = sample_rate,
        sample_mode    = AcquisitionType.CONTINUOUS,
        samps_per_chan = total_samples,
    )
    task.write(all_words, auto_start=False)
    task.start()

    _sine_task = task
    print(f"[sine] Running on DAC{dac_num} CH{ch_num} — "
          f"±{act_amp:.3f}V + {act_off:.3f}V DC  "
          f"({total_samples} words @ {sample_rate} S/s)")
    return task


def stop_sine() -> None:
    global _sine_task
    if _sine_task is not None:
        try: _sine_task.stop(); _sine_task.close()
        except Exception: pass
        _sine_task = None
        print("[sine] Stopped.")


# ══════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════

def clear_all(num_dacs=NUM_DACS, device=DEVICE) -> None:
    global _state
    with _Bus() as bus: _clear_all(bus, num_dacs)
    _state = [[0.0]*NUM_CH for _ in range(NUM_DACS)]
    print("All DACs cleared to 0V.")

def get_voltage(dac_num: int, ch_num: int) -> float:
    return _state[dac_num-1][ch_num-1]

def print_state() -> None:
    print("\n── AD5676R State (V) " + "─"*31)
    print("     " + "".join(f"  DAC{d+1}" for d in range(NUM_DACS)))
    for ch in range(NUM_CH):
        print(f"CH{ch+1:2d} " + "".join(f"  {_state[d][ch]:5.3f}" for d in range(NUM_DACS)))
    print("─"*51 + "\n")