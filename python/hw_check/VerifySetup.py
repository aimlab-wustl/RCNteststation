"""
verify_setup.py
Drop in your project root and run:  python verify_setup.py
Checks every file and import without touching any hardware.
"""

import sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
HW   = os.path.join(ROOT, "hardware")

print("=" * 60)
print("  Setup Verification")
print("=" * 60)
print(f"Project root : {ROOT}")
print(f"Python       : {sys.executable}")
print()

# ── 1. Check files exist ──────────────────────────────────────
required = [
    "config.py",
    "hardware/__init__.py",
    "hardware/dac_ad5676r.py",
    "hardware/dac_ltc2600.py",
    "hardware/device.py",
    "hardware/ai.py",
    "hardware/ao.py",
    "hardware/dio.py",
    "hardware/pfi.py",
]
print("[ FILE CHECK ]")
all_ok = True
for f in required:
    path = os.path.join(ROOT, f)
    exists = os.path.isfile(path)
    print(f"  {'✓' if exists else '✗'} {f}")
    if not exists:
        all_ok = False

# Warn if old dac.py still exists
old_dac = os.path.join(HW, "dac.py")
if os.path.isfile(old_dac):
    print(f"  ⚠  hardware/dac.py EXISTS — this old file may be imported instead of dac_ad5676r.py")
    print(f"     → DELETE hardware/dac.py")
    all_ok = False

print()

# ── 2. Check config.py has the right constants ────────────────
print("[ CONFIG CHECK ]")
sys.path.insert(0, ROOT)
try:
    import config
    checks = [
        ("DEVICE",            config.DEVICE),
        ("DAC_VERSION",       config.DAC_VERSION),
        ("AD5676R_PIN_RESET", getattr(config, "AD5676R_PIN_RESET", "MISSING")),
        ("AD5676R_PIN_SDI",   getattr(config, "AD5676R_PIN_SDI",   "MISSING")),
        ("AD5676R_PIN_SCK",   getattr(config, "AD5676R_PIN_SCK",   "MISSING")),
        ("AD5676R_PIN_SYNC",  getattr(config, "AD5676R_PIN_SYNC",  "MISSING")),
        ("AD5676R_VMAX",      getattr(config, "AD5676R_VMAX",      "MISSING")),
        ("LTC2600_PIN_CLR",   getattr(config, "LTC2600_PIN_CLR",   "MISSING")),
        ("LTC2600_VREF",      getattr(config, "LTC2600_VREF",      "MISSING")),
    ]
    for name, val in checks:
        ok = val != "MISSING"
        print(f"  {'✓' if ok else '✗'} {name} = {val}")
        if not ok:
            all_ok = False
except Exception as e:
    print(f"  ✗ Could not import config.py: {e}")
    all_ok = False

print()

# ── 3. Check __init__.py imports the right dac module ─────────
print("[ __init__.py CHECK ]")
init_path = os.path.join(HW, "__init__.py")
if os.path.isfile(init_path):
    content = open(init_path).read()
    if "from .dac import" in content and "from .dac_ad5676r import" not in content:
        print("  ✗ __init__.py still imports 'from .dac import' (old name)")
        print("    → Replace with 'from .dac_ad5676r import ...'")
        all_ok = False
    elif "from .dac_ad5676r import" in content:
        print("  ✓ __init__.py imports from .dac_ad5676r")
    if "from .dac_ltc2600 import" in content:
        print("  ✓ __init__.py imports from .dac_ltc2600")

print()

# ── 4. Try importing hardware package ─────────────────────────
print("[ IMPORT CHECK ]")
try:
    import hardware
    print("  ✓ import hardware succeeded")
    
    funcs = ["dac_initialize", "set_voltage", "dac_clear_all", "dac_print_state"]
    for f in funcs:
        has = hasattr(hardware, f)
        print(f"  {'✓' if has else '✗'} hardware.{f}")
        if not has:
            all_ok = False

    # Show which dac module is actually loaded
    import hardware.dac_ad5676r as _dac
    print(f"  ✓ dac_ad5676r loaded — DEVICE='{_dac.DEVICE}' VMAX={_dac.VMAX}")
    print(f"    _LO={_dac._LO} _HI={_dac._HI}")
    print(f"    _B_RESET={_dac._B_RESET} _B_SDI={_dac._B_SDI} "
          f"_B_SCK={_dac._B_SCK} _B_SYNC={_dac._B_SYNC}")
    print(f"    _IDLE={_dac._IDLE} (0b{_dac._IDLE:04b}) — "
          f"RESET={'H' if _dac._IDLE>>_dac._B_RESET&1 else 'L'} "
          f"SYNC={'H' if _dac._IDLE>>_dac._B_SYNC&1 else 'L'}")

except Exception as e:
    print(f"  ✗ Import failed: {e}")
    import traceback; traceback.print_exc()
    all_ok = False

print()

# ── 5. __pycache__ warning ────────────────────────────────────
print("[ PYCACHE CHECK ]")
cache_dir = os.path.join(HW, "__pycache__")
if os.path.isdir(cache_dir):
    pyc_files = os.listdir(cache_dir)
    print(f"  hardware/__pycache__/ has {len(pyc_files)} file(s)")
    if not all_ok:
        print("  ⚠  Since errors were found above, stale cache may be hiding them.")
        print("     → DELETE hardware/__pycache__/ and run again")
else:
    print("  ✓ No __pycache__ (clean)")

print()
print("=" * 60)
if all_ok:
    print("  ALL CHECKS PASSED — structure is correct")
    print("  If hardware still doesn't respond, the issue is wiring.")
else:
    print("  ISSUES FOUND — fix the ✗ items above then run again")
print("=" * 60)