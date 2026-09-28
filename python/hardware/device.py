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
# hardware/device.py — DAQ Device Initialization
# Creates and validates the nidaqmx system connection.
# All other hardware modules import DEVICE_NAME from here
# (or directly from config.py).
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # project root

import nidaqmx
import nidaqmx.system
from config import DEVICE


def list_devices() -> list[str]:
    """Return names of all NI-DAQmx devices visible on this machine."""
    system = nidaqmx.system.System.local()
    return [dev.name for dev in system.devices]


def verify_device(device_name: str = DEVICE) -> bool:
    """
    Check that the requested device is present and reachable.
    Prints a clear message either way.
    Returns True if found, False otherwise.
    """
    found = list_devices()
    if device_name in found:
        system = nidaqmx.system.System.local()
        dev = system.devices[device_name]
        print(f"[device] ✓ Found: {device_name}  ({dev.product_type})")
        return True
    else:
        print(f"[device] ✗ '{device_name}' not found.")
        print(f"[device]   Devices visible: {found if found else 'none'}")
        print("[device]   Check NI MAX or your USB connection.")
        return False


def initialize(device_name: str = DEVICE) -> bool:
    """
    Entry-point called by main.py (or __init__.py) at startup.
    Returns True on success, raises RuntimeError on failure.
    """
    print("=" * 50)
    print("  NI DAQ Initialization")
    print("=" * 50)

    if not verify_device(device_name):
        raise RuntimeError(
            f"DAQ device '{device_name}' not found. "
            "Check USB connection and NI-DAQmx driver."
        )

    print("[device] Initialization complete.\n")
    return True


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    initialize()