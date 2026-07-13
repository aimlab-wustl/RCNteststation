# ============================================================
# test_dac.py — DAC smoke test
#
# Same code works for any DAC version. Switch DAC_VERSION
# in config.py between "AD5676R" / "LTC2600" / "DAC80508".
# ============================================================

from config import DAC_VERSION, DAC_NUM_DACS, DAC_NUM_CH
from hardware import (
    dac_initialize, set_voltage, dac_clear_all,
    get_voltage, dac_print_state,
)


def main():
    print(f"\n[test_dac] Active DAC: {DAC_VERSION}\n")

    # dac_initialize()
    dac_initialize(use_external_ref=True)

    print("\n[test_dac] Setting a few channels...")
    set_voltage(1, 1, 1.0)
    set_voltage(2, 3, 2.5)
    set_voltage(4, 1, 3.7)

    dac_print_state()

    print(f"[test_dac] readback DAC1 CH1 = {get_voltage(1,1):.3f}V")



if __name__ == "__main__":
    main()
