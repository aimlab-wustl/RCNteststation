/*
 * Project: Automated Analog and Neuromorphic Integrated Circuits Test Station
 * Author: Kaiyuan (Sam) Kang
 *
 * Licensing Terms: This program is licensed under the Creative Commons
 * Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
 * You are free to share and adapt this program for noncommercial purposes,
 * provided that appropriate credit is given, a link to the license is provided,
 * and any modifications are indicated. Commercial use requires a separate
 * license from the copyright holder. See the LICENSE file for the complete
 * license terms.
 *
 * NO WARRANTY: BECAUSE THE PROGRAM IS LICENSED FREE OF CHARGE, THERE IS NO
 * WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW.
 * EXCEPT WHEN OTHERWISE STATED IN WRITING, THE COPYRIGHT HOLDERS AND/OR
 * OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY OF ANY KIND,
 * EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
 * ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.
 * SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY
 * SERVICING, REPAIR, OR CORRECTION. IN NO EVENT, UNLESS REQUIRED BY
 * APPLICABLE LAW OR AGREED TO IN WRITING, WILL ANY COPYRIGHT HOLDER OR ANY
 * OTHER PARTY WHO MAY MODIFY AND/OR REDISTRIBUTE THE PROGRAM BE LIABLE TO
 * YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL, OR
 * CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE
 * PROGRAM (INCLUDING, BUT NOT LIMITED TO, LOSS OF DATA, DATA BEING
 * RENDERED INACCURATE, LOSSES SUSTAINED BY YOU OR THIRD PARTIES, OR A
 * FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER PROGRAMS), EVEN IF SUCH
 * HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
 * DAMAGES.
 */
 /* =============================================================
 * tia.h — OPA3S328 TIA gain select driver
 * AIMLAB_TESTSTATION_V3 / STM32H743
 *
 * Pin mapping (confirmed from schematic):
 *   PE6  = SELB1   (STM32 pin 37)
 *   PE7  = SELB0   (STM32 pin 38)
 *   PE8  = SELA0   (STM32 pin 39)
 *   PE9  = SELA1   (STM32 pin 40)
 *
 * Amp A feedback (OUTA → ADS131 Ch3, differential vs 2.5V REGREF):
 *   GAIN_A_2K    SELA1=0 SELA0=0  →  OUTSA1 closed  (2kΩ,   ±1.22mA)
 *   GAIN_A_20K   SELA1=0 SELA0=1  →  OUTSA2 closed  (20kΩ,  ±122µA)
 *
 * Amp B feedback (OUTB → ADS131 Ch4, differential vs 2.5V REGREF):
 *   GAIN_B_20K   SELB1=0 SELB0=0  →  OUTSB1 closed  (20kΩ,  ±122µA)
 *   GAIN_B_200K  SELB1=0 SELB0=1  →  OUTSB2 closed  (200kΩ, ±12.2µA)
 *   GAIN_B_2M    SELB1=1 SELB0=0  →  OUTSB3 closed  (2MΩ,   ±1.22µA)
 *
 * FORBIDDEN: SELA1=1 AND SELA0=1 simultaneously (special shutdown mode).
 *            This driver never generates that combination.
 *
 * Switch RON note: ~84-125Ω in series with feedback resistor.
 *   Calibrate out in Python — do not correct in firmware.
 * =============================================================*/

#ifndef TIA_H
#define TIA_H

#include "main.h"
#include <stdint.h>

/* ── Amp A gain range identifiers ───────────────────────────────────────── */
typedef enum {
    TIA_A_OFF   = 0,   /* SELA1=0 SELA0=0 — OUTSA1 closed (2kΩ default)    */
                       /* Use TIA_A_2K explicitly; OFF kept for completeness */
    TIA_A_2K    = 1,   /* SELA1=0 SELA0=0 → OUTSA1 → 2kΩ  ±1.22mA         */
    TIA_A_20K   = 2,   /* SELA1=0 SELA0=1 → OUTSA2 → 20kΩ ±122µA          */
} TIA_GainA_t;

/* ── Amp B gain range identifiers ───────────────────────────────────────── */
typedef enum {
    TIA_B_20K   = 1,   /* SELB1=0 SELB0=0 → OUTSB1 → 20kΩ  ±122µA         */
    TIA_B_200K  = 2,   /* SELB1=0 SELB0=1 → OUTSB2 → 200kΩ ±12.2µA        */
    TIA_B_2M    = 3,   /* SELB1=1 SELB0=0 → OUTSB3 → 2MΩ   ±1.22µA        */
    TIA_B_OFF   = 4,   /* SELB1=1 SELB0=1 → all B switches open             */
} TIA_GainB_t;

/* ── Full gain state (both amps) ────────────────────────────────────────── */
typedef struct {
    TIA_GainA_t amp_a;
    TIA_GainB_t amp_b;
} TIA_State_t;

/* ── API ─────────────────────────────────────────────────────────────────── */

/* Initialise — drives all SEL pins low (Amp A: 2kΩ, Amp B: 20kΩ).
 * Call once at boot, after MX_GPIO_Init(). */
void TIA_Init(void);

/* Set Amp A feedback resistor. Returns 0 on success, -1 if gain invalid. */
int  TIA_SetGainA(TIA_GainA_t gain);

/* Set Amp B feedback resistor. Returns 0 on success, -1 if gain invalid. */
int  TIA_SetGainB(TIA_GainB_t gain);

/* Read back currently active gain state. */
TIA_State_t TIA_GetState(void);

/* Return nominal feedback resistance in ohms for logging/calibration.
 * Does NOT include switch RON (~100Ω) — calibrate that in Python. */
uint32_t TIA_GetRfA(void);
uint32_t TIA_GetRfB(void);

#endif /* TIA_H */
