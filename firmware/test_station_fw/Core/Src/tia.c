/*
 * tia.c — OPA3S328 TIA gain select driver
 * AIMLAB_TESTSTATION_V3 / STM32H743
 *
 * Drives PE6/PE7/PE8/PE9 (SELB1/SELB0/SELA0/SELA1) to select the
 * active feedback resistor on each OPA3S328 amplifier channel.
 *
 * Pin names (from main.h, defined by CubeMX):
 *   SELB1_Pin  = PE6
 *   SELB0_Pin  = PE7
 *   SELA0_Pin  = PE8
 *   SELA1_Pin  = PE9
 *
 * All four pins are already configured as GPIO_Output push-pull by
 * MX_GPIO_Init() and initialised LOW.  This driver only calls
 * HAL_GPIO_WritePin — no re-init needed.
 */

#include "tia.h"

/* ── Internal state ────────────────────────────────────────────────────── */
static TIA_GainA_t _gain_a = TIA_A_2K;   /* boot default: OUTSA1 / 2kΩ  */
static TIA_GainB_t _gain_b = TIA_B_20K;  /* boot default: OUTSB1 / 20kΩ */

/* ── Low-level pin write helpers ────────────────────────────────────────── */
static inline void _set_sela(uint8_t sela1, uint8_t sela0)
{
    /*
     * SAFETY: Never write SELA1=1 AND SELA0=1 simultaneously.
     * That combination triggers OPA3S328 special mode (Table 4-3),
     * which overrides SELB decode and may power down both amplifiers.
     *
     * Safe sequencing: always clear before set to avoid a glitch
     * through the forbidden state when transitioning between ranges.
     */
    HAL_GPIO_WritePin(GPIOE, SELA1_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, SELA0_Pin, GPIO_PIN_RESET);
    /* Now apply the target state */
    HAL_GPIO_WritePin(GPIOE, SELA1_Pin,
                      sela1 ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, SELA0_Pin,
                      sela0 ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static inline void _set_selb(uint8_t selb1, uint8_t selb0)
{
    /* No forbidden state on SELB side (SELB1=SELB0=1 just opens all
     * B switches — valid but we expose it as TIA_B_OFF for clarity).
     * Still clear-before-set for consistency and glitch avoidance. */
    HAL_GPIO_WritePin(GPIOE, SELB1_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, SELB0_Pin, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, SELB1_Pin,
                      selb1 ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOE, SELB0_Pin,
                      selb0 ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ── Public API ─────────────────────────────────────────────────────────── */

void TIA_Init(void)
{
    /* MX_GPIO_Init already drives all SEL pins low.
     * Call _set_sela / _set_selb anyway to sync internal state
     * and guarantee the hardware matches our boot defaults. */
    _set_sela(0, 0);   /* OUTSA1 → 2kΩ  */
    _set_selb(0, 0);   /* OUTSB1 → 20kΩ */
    _gain_a = TIA_A_2K;
    _gain_b = TIA_B_20K;
}

int TIA_SetGainA(TIA_GainA_t gain)
{
    switch (gain)
    {
        case TIA_A_2K:   /* SELA1=0 SELA0=0 */
            _set_sela(0, 0);
            break;
        case TIA_A_20K:  /* SELA1=0 SELA0=1 */
            _set_sela(0, 1);
            break;
        default:
            return -1;   /* Invalid gain — do not change hardware */
    }
    _gain_a = gain;
    return 0;
}

int TIA_SetGainB(TIA_GainB_t gain)
{
    switch (gain)
    {
        case TIA_B_20K:  /* SELB1=0 SELB0=0 */
            _set_selb(0, 0);
            break;
        case TIA_B_200K: /* SELB1=0 SELB0=1 */
            _set_selb(0, 1);
            break;
        case TIA_B_2M:   /* SELB1=1 SELB0=0 */
            _set_selb(1, 0);
            break;
        case TIA_B_OFF:  /* SELB1=1 SELB0=1 — all B switches open */
            _set_selb(1, 1);
            break;
        default:
            return -1;
    }
    _gain_b = gain;
    return 0;
}

TIA_State_t TIA_GetState(void)
{
    TIA_State_t s = { _gain_a, _gain_b };
    return s;
}

uint32_t TIA_GetRfA(void)
{
    switch (_gain_a) {
        case TIA_A_2K:  return 2000;
        case TIA_A_20K: return 20000;
        default:        return 0;
    }
}

uint32_t TIA_GetRfB(void)
{
    switch (_gain_b) {
        case TIA_B_20K:  return 20000;
        case TIA_B_200K: return 200000;
        case TIA_B_2M:   return 2000000;
        default:         return 0;
    }
}
