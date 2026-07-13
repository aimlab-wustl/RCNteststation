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