# Project: Automated Analog and Neuromorphic Integrated Circuits Test Station
# Author: Kaiyuan (Sam) Kang
#
# Licensing Terms: This program is licensed under the Creative Commons
# Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You are free to share and adapt this program for noncommercial purposes,
# provided that appropriate credit is given, a link to the license is provided,
# and any modifications are indicated. Commercial use requires a separate
# license from the copyright holder. See the LICENSE file for the complete
# license terms.
#
# NO WARRANTY: BECAUSE THE PROGRAM IS LICENSED FREE OF CHARGE, THERE IS NO
# WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW.
# EXCEPT WHEN OTHERWISE STATED IN WRITING, THE COPYRIGHT HOLDERS AND/OR
# OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
# ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.
# SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY
# SERVICING, REPAIR, OR CORRECTION. IN NO EVENT, UNLESS REQUIRED BY
# APPLICABLE LAW OR AGREED TO IN WRITING, WILL ANY COPYRIGHT HOLDER OR ANY
# OTHER PARTY WHO MAY MODIFY AND/OR REDISTRIBUTE THE PROGRAM BE LIABLE TO
# YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL, OR
# CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE
# PROGRAM (INCLUDING, BUT NOT LIMITED TO, LOSS OF DATA, DATA BEING
# RENDERED INACCURATE, LOSSES SUSTAINED BY YOU OR THIRD PARTIES, OR A
# FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH
# HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGES.
#
# ============================================================
# hardware/stm_dac.py — DAC80508 Python driver via STM32 CDC
# AIMLAB_TESTSTATION_V3
#
# Sends ASCII commands to STM32 cmd_parser.c over USB CDC.
# Transport layer: hardware/cdc_serial.py (COM4)
#
# STM32 command set (from cmd_parser.c dispatch table):
#   DAC_SET <chip 1-5> <ch 1-8> <voltage 0.0-5.0>
#   DAC_SET_ALL <voltage 0.0-5.0>
#   DAC_CLEAR
#
# STM32 responses:
#   OK:DAC_C1_CH1=10000mV   (voltage in 0.1mV units, ÷10000 = V)
#   OK:DAC_ALL=25000mV
#   OK:DAC_ALL=0.0000V
#   ERR:...
#
# Public API:
#   initialize()                  call DAC_CLEAR to zero all outputs
#   set_voltage(chip, ch, V)      set one channel
#   set_all(V)                    set all 40 outputs to same voltage
#   clear_all()                   zero all 40 outputs
#   get_voltage(chip, ch)         return last commanded voltage (Python state)
#   print_state()                 print 5×8 voltage table
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    DAC_NUM_DACS, DAC_NUM_CH,
    DAC80508_VMIN, DAC80508_VMAX,
)
from hardware.cdc_serial import open_port, send_command

# ── Python-side shadow state ──────────────────────────────────
# Mirrors what was last commanded to the STM32.
# Not read back from hardware — pure bookkeeping.
_state = [[0.0] * DAC_NUM_CH for _ in range(DAC_NUM_DACS)]


# ════════════════════════════════════════════════════════════════
# Internal helpers
# ════════════════════════════════════════════════════════════════

def _clamp(v: float) -> float:
    return max(float(DAC80508_VMIN), min(float(v), float(DAC80508_VMAX)))


def _validate(chip: int, ch: int):
    if not (1 <= chip <= DAC_NUM_DACS):
        raise ValueError(f"chip must be 1..{DAC_NUM_DACS}, got {chip}")
    if not (1 <= ch <= DAC_NUM_CH):
        raise ValueError(f"ch must be 1..{DAC_NUM_CH}, got {ch}")


# ════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════

def initialize() -> bool:
    """
    Zero all 40 DAC outputs via DAC_CLEAR.
    Call once at startup before set_voltage().
    Port is opened automatically if not already open.
    """
    global _state
    open_port()
    resp = send_command("DAC_CLEAR")
    ok = resp.startswith("OK:")
    if ok:
        _state = [[0.0] * DAC_NUM_CH for _ in range(DAC_NUM_DACS)]
        print("DAC80508 initialized — all outputs 0 V.")
    else:
        print(f"[stm_dac] DAC_CLEAR failed: {resp}")
    return ok


def set_voltage(chip: int, ch: int, voltage: float) -> bool:
    """
    Set one DAC channel.

    Args:
        chip:    1–5
        ch:      1–8  (1 = OUT0, 8 = OUT7)
        voltage: 0.0–5.0 V (clamped silently)

    Returns:
        True on success.
    """
    _validate(chip, ch)
    v = _clamp(voltage)
    open_port()
    resp = send_command(f"DAC_SET {chip} {ch} {v:.4f}")
    ok = resp.startswith("OK:")
    if ok:
        _state[chip - 1][ch - 1] = v
        print(f"DAC{chip} CH{ch}/OUT{ch-1} = {v:.4f} V")
    else:
        print(f"[stm_dac] DAC_SET failed: {resp}")
    return ok


def set_all(voltage: float) -> bool:
    """
    Set all 40 outputs to the same voltage.

    Args:
        voltage: 0.0–5.0 V (clamped silently)

    Returns:
        True on success.
    """
    global _state
    v = _clamp(voltage)
    open_port()
    resp = send_command(f"DAC_SET_ALL {v:.4f}")
    ok = resp.startswith("OK:")
    if ok:
        _state = [[v] * DAC_NUM_CH for _ in range(DAC_NUM_DACS)]
        print(f"All DAC outputs = {v:.4f} V")
    else:
        print(f"[stm_dac] DAC_SET_ALL failed: {resp}")
    return ok


def clear_all() -> bool:
    """
    Zero all 40 outputs.

    Returns:
        True on success.
    """
    global _state
    open_port()
    resp = send_command("DAC_CLEAR")
    ok = resp.startswith("OK:")
    if ok:
        _state = [[0.0] * DAC_NUM_CH for _ in range(DAC_NUM_DACS)]
        print("All DAC outputs cleared to 0 V.")
    else:
        print(f"[stm_dac] DAC_CLEAR failed: {resp}")
    return ok


def get_voltage(chip: int, ch: int) -> float:
    """Return last commanded voltage for chip/channel (Python state only)."""
    _validate(chip, ch)
    return _state[chip - 1][ch - 1]


def print_state() -> None:
    """Print the 5×8 last-commanded voltage table."""
    print("\n── STM32 DAC80508 State (V) " + "─" * 23)
    print("     " + "".join(f"  DAC{d+1}" for d in range(DAC_NUM_DACS)))
    for ch in range(DAC_NUM_CH):
        print(f"CH{ch+1:2d} " +
              "".join(f"  {_state[d][ch]:5.3f}" for d in range(DAC_NUM_DACS)))
    print("─" * 51 + "\n")


# ════════════════════════════════════════════════════════════════
# Quick self-test
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    initialize()

    print("\nStaircase test — chip N → N volts on CH1:")
    set_voltage(1, 1, 1.0)
    set_voltage(2, 1, 2.0)
    set_voltage(3, 1, 3.0)
    set_voltage(4, 1, 4.0)
    set_voltage(5, 1, 5.0)

    print_state()
    input("\nMeasure outputs, then press Enter to clear and exit...")
    clear_all()