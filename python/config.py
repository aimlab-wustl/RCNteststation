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