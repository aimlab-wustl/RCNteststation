# ============================================================
# hardware/__init__.py
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DAC_VERSION

from .device import initialize, verify_device, list_devices
from .ai     import read_single, read_buffered, read_continuous
from .ao     import write_single, write_all, zero_all
from .dio    import (
    DIOOutputSession, loopback_line,
    set_line, get_line, set_port, get_port,
)
from .pfi    import (
    generate_pulse, stop_pulse,
    count_edges, measure_frequency, arm_ai_trigger,
)

# ── DAC driver — switch by setting DAC_VERSION in config.py ──
if DAC_VERSION == "AD5676R":
    from .dac_ad5676r import (
        initialize  as dac_initialize,
        set_voltage,
        clear_all   as dac_clear_all,
        get_voltage,
        print_state as dac_print_state,
    )
elif DAC_VERSION == "LTC2600":
    from .dac_ltc2600 import (
        initialize  as dac_initialize,
        set_voltage,
        clear_all   as dac_clear_all,
        get_voltage,
        print_state as dac_print_state,
    )
elif DAC_VERSION == "DAC80508":
    from .dac_dac80508 import (
        initialize  as dac_initialize,
        set_voltage,
        clear_all   as dac_clear_all,
        get_voltage,
        print_state as dac_print_state,
    )
else:
    raise ImportError(
        f"Unknown DAC_VERSION='{DAC_VERSION}' in config.py. "
        "Valid: 'AD5676R', 'LTC2600', 'DAC80508'"
    )

__all__ = [
    # device
    "initialize", "verify_device", "list_devices",
    # ai
    "read_single", "read_buffered", "read_continuous",
    # ao
    "write_single", "write_all", "zero_all",
    # dio
    "DIOOutputSession", "loopback_line",
    "set_line", "get_line", "set_port", "get_port",
    # pfi
    "generate_pulse", "stop_pulse",
    "count_edges", "measure_frequency", "arm_ai_trigger",
    # dac (version-agnostic)
    "dac_initialize", "set_voltage", "dac_clear_all",
    "get_voltage", "dac_print_state",
]