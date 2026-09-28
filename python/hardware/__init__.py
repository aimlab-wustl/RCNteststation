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