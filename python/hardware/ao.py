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
# hardware/ao.py — Analog Output
# Covers:
#   • write_single()  — write one voltage to one channel
#   • write_all()     — write voltages to all AO channels at once
#   • zero_all()      — set all outputs to 0V safely
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import nidaqmx
from config import DEVICE, AO_CHANNELS, AO_VOLTAGE_RANGE


def _clamp(value: float) -> float:
    """Clamp value to the configured AO voltage range."""
    lo, hi = AO_VOLTAGE_RANGE
    if value < lo:
        print(f"[ao] WARNING: {value:.4f}V below min {lo}V — clamped.")
        return lo
    if value > hi:
        print(f"[ao] WARNING: {value:.4f}V above max {hi}V — clamped.")
        return hi
    return value


def write_single(channel: int, voltage: float, device: str = DEVICE) -> None:
    """
    Write a voltage to one AO channel.

    Args:
        channel: AO channel index (e.g. 0 → ao0)
        voltage: output voltage in volts
        device:  DAQ device name

    Example:
        write_single(0, 2.5)   # ao0 = 2.5V
    """
    voltage = _clamp(voltage)
    ch_str = f"{device}/ao{channel}"
    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan(
            ch_str,
            min_val=AO_VOLTAGE_RANGE[0],
            max_val=AO_VOLTAGE_RANGE[1],
        )
        task.write(voltage)
    print(f"[ao] ao{channel} = {voltage:.4f}V")


def write_all(voltages: list[float], device: str = DEVICE) -> None:
    """
    Write voltages to all configured AO channels simultaneously.

    Args:
        voltages: list of voltages, one per channel in AO_CHANNELS order
        device:   DAQ device name

    Example:
        write_all([1.0, 2.5])   # ao0=1.0V, ao1=2.5V
    """
    if len(voltages) != len(AO_CHANNELS):
        raise ValueError(
            f"Expected {len(AO_CHANNELS)} voltages, got {len(voltages)}"
        )
    clamped = [_clamp(v) for v in voltages]
    ch_str = ", ".join(f"{device}/ao{c}" for c in AO_CHANNELS)

    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan(
            ch_str,
            min_val=AO_VOLTAGE_RANGE[0],
            max_val=AO_VOLTAGE_RANGE[1],
        )
        task.write(clamped)

    for ch, v in zip(AO_CHANNELS, clamped):
        print(f"[ao] ao{ch} = {v:.4f}V")


def zero_all(device: str = DEVICE) -> None:
    """Set all AO channels to 0V. Call this on shutdown or init."""
    lo = AO_VOLTAGE_RANGE[0]
    write_all([lo] * len(AO_CHANNELS), device=device)
    print("[ao] All outputs zeroed.")


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    write_single(0, 1.23)
    zero_all()