/* =============================================================
 * adc_capture.h — Timer-triggered, DMA-fed burst capture on ADC1/PA1
 * AIMLAB_TESTSTATION_V3  /  STM32H743
 *
 * PURELY ADDITIVE — does not modify MX_ADC1_Init(), does not touch
 * ADC_ReadVoltage(), does not require any main.c changes. ADC1 is
 * temporarily reconfigured into external-trigger+DMA mode for the
 * duration of one capture, then automatically restored to its
 * original software-trigger polling config (what ADC_ReadVoltage(),
 * STATUS, and STMADC_STREAM all rely on) once the buffer is full.
 *
 * Hardware used (all newly claimed, verified clear of existing use):
 *   TIM1/TRGO2 — a second, ADC-dedicated trigger output only present
 *                on advanced timers (TIM1/TIM8). No GPIO pins are
 *                configured or touched -- only TIM1's internal
 *                trigger generation is used, so this cannot conflict
 *                with anything else on the board. (TIM6's regular
 *                TRGO does NOT reliably trigger the ADC on STM32H7 --
 *                a documented, widely-reported silicon/HAL quirk,
 *                confirmed independently by multiple engineers on
 *                H743 and H753 -- hence TIM1/TRGO2 instead.)
 *   DMA2_Stream0 — confirmed different controller from DMA1_Stream3
 *                  (SPI2_RX / ADS131A04, per stm32h7xx_hal_msp.c)
 *   ADC1 channel 17 (PA1) — SAME channel ADC_ReadVoltage(1) uses,
 *                  just temporarily driven differently
 *
 * Buffer: placed in the same non-cacheable .dma_buffers MPU region
 * (0x30000000, 32KB) the ADS131A04 ring buffers already use. That
 * region currently holds ~7.7KB for ADS131A04; this module's default
 * 8000-sample buffer (16KB) fits comfortably in the remainder.
 *
 * Clock math -- CONFIRMED for TIM6/APB1, ASSUMED (not yet
 * independently verified) for TIM1/APB2:
 *   HSE=8MHz (confirmed via the MCO1=8MHz MCLK output) -> PLL1 ->
 *   480MHz SYSCLK -> AHB/DIV2 = 240MHz HCLK. APB1/DIV2 -> PCLK1=120MHz
 *   -> TIM6 kernel clock = 2x PCLK1 = 240MHz (confirmed, standard
 *   STM32 "APB prescaler != 1 doubles timer clock" rule). TIM1 is on
 *   APB2, not APB1 -- if APB2 uses the same DIV2 prescaler (common,
 *   but NOT independently confirmed from SystemClock_Config), TIM1's
 *   clock would also be 240MHz by the same doubling rule. Cross-check
 *   the actual achieved rate against ADCFAST_DBG's elapsed_ms
 *   (measured, not computed) before trusting exact timing.
 *
 *   sample_rate = 240MHz / (prescaler+1) / (period+1)   [ASSUMED]
 *
 *   Start here (easy to sanity-check by hand):
 *     prescaler=23, period=999   -> ASSUMED 10.000 kSPS
 *   Push toward the ADC's real ceiling only after that's verified:
 *     prescaler=0,  period=74    -> ASSUMED 3.2 MSPS
 *     (ADC ceiling = 32MHz ADC clock / 10 cycles (1.5 sample + 8.5
 *      convert, 16-bit) = 3.2 MSPS with the CURRENT ADC clock config
 *      -- ADC_CLOCK_ASYNC_DIV2 off HSI=64MHz, already set, no changes
 *      needed there either)
 * =============================================================*/

#ifndef ADC_CAPTURE_H
#define ADC_CAPTURE_H

#include "main.h"
#include <stdint.h>

#define ADCFAST_MAX_SAMPLES   8000   /* 16KB -- fits the remaining
                                        ~25KB of the .dma_buffers region */

extern volatile uint8_t  g_capture_done;
extern volatile uint32_t g_capture_n;      /* samples actually requested */

/* Debug visibility -- see adc_capture.c for what each one means.
 * Read these via the ADCFAST_DBG command in cmd_parser.c.
 * Status values: 0=HAL_OK, 1=HAL_ERROR, 2=HAL_BUSY, 3=HAL_TIMEOUT. */
extern volatile uint32_t g_dbg_dma_init_status;
extern volatile uint32_t g_dbg_adc_init_status;
extern volatile uint32_t g_dbg_adc_start_dma_status;
extern volatile uint32_t g_dbg_tim_start_status;
extern volatile uint32_t g_dbg_convcplt_fired_count;
extern volatile uint32_t g_dbg_capture_elapsed_ms;   /* MEASURED (via
                                                         HAL_GetTick()),
                                                         not computed --
                                                         the real check
                                                         on whether the
                                                         assumed rate
                                                         is correct */
extern volatile uint32_t g_dbg_adc_error_count;       /* ADC/DMA overrun
                                                          count -- only
                                                          a real risk
                                                          near the rate
                                                          ceiling */

/* Raw ADC codes (16-bit, single-ended, 0..65535 over 0..3.3V) land here.
 * Valid only after g_capture_done goes high following ADC_Capture_Start(). */
extern uint16_t g_adcfast_buf[ADCFAST_MAX_SAMPLES];

/* Arms TIM1/TRGO2 + DMA2_Stream0 + ADC1 (temporarily reconfigured),
 * starts the timer, and returns immediately -- capture runs in the
 * background via DMA/ISR, no CPU polling loop required.
 * n_samples capped internally at ADCFAST_MAX_SAMPLES.
 * Returns 0 if a capture is already in progress, 1 otherwise. */
uint8_t ADC_Capture_Start(uint32_t n_samples, uint32_t prescaler, uint32_t period);

#endif /* ADC_CAPTURE_H */
