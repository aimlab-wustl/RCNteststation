"""
test_ad5676r.py  —  Quick voltage test for AD5676R
Run from the project root: python test_ad5676r.py
"""

from hardware import dac_initialize, set_voltage, dac_clear_all, dac_print_state

# ── Initialize ────────────────────────────────────────────────
dac_initialize()

# ── Set some voltages — measure these with your DMM ──────────
set_voltage(1, 1, 2.0)    # DAC1 CH1 → expect 0.0V
set_voltage(3, 2, 2.0)    # DAC1 CH2 → expect 1.0V
set_voltage(1, 3, 2.5)    # DAC1 CH3 → expect 2.5V
set_voltage(4, 4, 1.0)    # DAC1 CH4 → expect 5.0V

# ── Print state table ─────────────────────────────────────────
dac_print_state()

# input("\nMeasure the outputs, then press Enter to clear all and exit...")

# dac_clear_all()