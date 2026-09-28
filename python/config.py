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
# config.py — Hardware Configuration
# Single source of truth for all device/pin/range constants.
# Edit this file when hardware changes; nothing else needs to.
# ============================================================

# ── DAQ Device ───────────────────────────────────────────────
DEVICE = "Dev1"                  # NI USB-6212; check NI MAX if unsure

# ── Analog Input ─────────────────────────────────────────────
AI_CHANNELS        = list(range(8))   # ai0 – ai7
AI_TERMINAL_CONFIG = "SingleEnded"    # or "Differential"
AI_VOLTAGE_RANGE   = (-10.0, 10.0)   # (min_V, max_V)
AI_DEFAULT_RATE    = 400_000          # Hz  (max single-ch on USB-6212)
AI_DEFAULT_SAMPLES = 4_000

# ── Analog Output ────────────────────────────────────────────
AO_CHANNELS      = [0, 1]
AO_VOLTAGE_RANGE = (0.0, 10.0)

# ── Digital I/O ──────────────────────────────────────────────
DIO_PORT = "port0"

# ── Counter / PFI ────────────────────────────────────────────
CTR_DEFAULT      = "ctr0"
PFI_DEFAULT_LINE = 0

# ── STM32 USB CDC connection ─────────────────────────────────
STM_COM_PORT  = "COM4"       # STM32 USB CDC port (check Device Manager)
STM_BAUD_RATE = 115200       # ignored by CDC but required by pyserial
STM_TIMEOUT   = 2.0          # seconds to wait for a response line

# ════════════════════════════════════════════════════════════════
# DAC VERSION SELECT
# ════════════════════════════════════════════════════════════════
# "AD5676R"  → hardware/dac_ad5676r.py  (V2 station, internal ref, 0–5 V)
# "LTC2600"  → hardware/dac_ltc2600.py  (V1 station, external VREF, 0–4 V)
# "DAC80508" → hardware/dac_dac80508.py (V3 station, STM32H7 board)
DAC_VERSION = "DAC80508"

# ── Shared DAC geometry ───────────────────────────────────────
DAC_NUM_DACS = 5
DAC_NUM_CH   = 8
DAC_BITS     = 16

# ── AD5676R pin + range (V2 station) ─────────────────────────
AD5676R_PIN_RESET = 1    # port0/line1
AD5676R_PIN_SDI   = 2    # port0/line2
AD5676R_PIN_SCK   = 3    # port0/line3
AD5676R_PIN_SYNC  = 4    # port0/line4
AD5676R_VMIN      = 0.0
AD5676R_VMAX      = 5.0  # internal ref × gain=2

# ── LTC2600 pin + range (V1 station) ─────────────────────────
LTC2600_PIN_CLR  = 0     # port0/line0
LTC2600_PIN_SDI  = 1     # port0/line1
LTC2600_PIN_SCK  = 2     # port0/line2
LTC2600_PIN_CS   = 3     # port0/line3
LTC2600_VMIN     = 0.0
LTC2600_VMAX     = 4.0   # = VREF; measure with DMM
LTC2600_VREF     = 4.0

# ── DAC80508 pin + range (V3 station) ────────────────────────
DAC80508_PIN_SDI  = 1    # port0/line1
DAC80508_PIN_SCK  = 2    # port0/line2
DAC80508_PIN_CSN  = 3    # port0/line3
DAC80508_VMIN     = 0.0
DAC80508_VMAX = 5.0  # 2.5 V ref (internal or external) × gain=2
# Reference mode selected at runtime via initialize(use_external_ref=True/False)