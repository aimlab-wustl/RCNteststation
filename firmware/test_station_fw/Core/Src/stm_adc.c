/* =============================================================
 * adc_capture.c — see adc_capture.h for full design rationale
 * AIMLAB_TESTSTATION_V3  /  STM32H743
 *
 * REVISION: switched TIM6/TRGO -> TIM1/TRGO2. TIM6 TRGO does not
 * reliably trigger the ADC on STM32H7 -- this is a documented,
 * widely-reported quirk (ST community: "STM32H7 triggering ADC
 * with TIM6 TRGO", reproduced independently on H743 and H753),
 * not a config error. TIM1's TRGO2 -- a second, ADC-dedicated
 * trigger output only present on advanced timers (TIM1/TIM8) --
 * is the confirmed-working alternative on H7. TIM1 has GPIO pins
 * associated with it normally (PWM channels), but none of those
 * are touched here -- only its internal trigger generation is
 * used, so this still cannot conflict with anything on the board.
 * =============================================================*/

#include "stm_adc.h"

extern ADC_HandleTypeDef hadc1;   /* declared in main.c, unchanged */

__attribute__((section(".dma_buffers")))
uint16_t g_adcfast_buf[ADCFAST_MAX_SAMPLES];

volatile uint8_t  g_capture_done = 1;   /* idle until first capture */
volatile uint32_t g_capture_n    = 0;

/* Debug visibility -- HAL_StatusTypeDef values (0=OK,1=ERROR,2=BUSY,
 * 3=TIMEOUT) from each critical call, plus an unconditional counter
 * so we can tell "callback never fired" apart from "fired for the
 * wrong ADC instance." Matches the g_dbg_* convention already used
 * in ads131a04.c. Read these back via a new ADCFAST_DBG command. */
volatile uint32_t g_dbg_dma_init_status      = 0xFF;
volatile uint32_t g_dbg_adc_init_status      = 0xFF;
volatile uint32_t g_dbg_adc_start_dma_status = 0xFF;
volatile uint32_t g_dbg_tim_start_status     = 0xFF;
volatile uint32_t g_dbg_convcplt_fired_count = 0;   /* unconditional,
                                                        before the
                                                        instance check */
volatile uint32_t g_dbg_capture_elapsed_ms   = 0;   /* measured, not
                                                        computed -- the
                                                        real check on
                                                        whether the
                                                        assumed rate
                                                        is actually
                                                        correct */
volatile uint32_t g_dbg_adc_error_count      = 0;   /* increments on
                                                        HAL_ADC_ErrorCallback
                                                        -- catches DMA/ADC
                                                        overrun at high
                                                        rates, which
                                                        would otherwise
                                                        silently corrupt
                                                        or skip samples */
static uint32_t _capture_start_tick = 0;

static TIM_HandleTypeDef htim1;
DMA_HandleTypeDef hdma_adc1;   /* NOT static -- stm32h7xx_it.c externs this */
static uint8_t _module_initialized = 0;
static uint8_t _capture_in_progress = 0;

static void _module_init(void)
{
    if (_module_initialized) return;

    /* TIM1 -- used ONLY for its internal TRGO2 generation. No GPIO
     * configured, no PWM channels enabled, no pins touched at all. */
    __HAL_RCC_TIM1_CLK_ENABLE();
    htim1.Instance               = TIM1;
    htim1.Init.Prescaler         = 23;
    htim1.Init.CounterMode       = TIM_COUNTERMODE_UP;
    htim1.Init.Period            = 999;
    htim1.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    HAL_TIM_Base_Init(&htim1);

    TIM_MasterConfigTypeDef master = {0};
    master.MasterOutputTrigger  = TIM_TRGO_RESET;    /* regular TRGO unused */
    master.MasterOutputTrigger2 = TIM_TRGO2_UPDATE;  /* THIS drives the ADC */
    master.MasterSlaveMode      = TIM_MASTERSLAVEMODE_DISABLE;
    HAL_TIMEx_MasterConfigSynchronization(&htim1, &master);

    __HAL_RCC_DMA2_CLK_ENABLE();
    hdma_adc1.Instance                 = DMA2_Stream0;
    hdma_adc1.Init.Request             = DMA_REQUEST_ADC1;
    hdma_adc1.Init.Direction           = DMA_PERIPH_TO_MEMORY;
    hdma_adc1.Init.PeriphInc           = DMA_PINC_DISABLE;
    hdma_adc1.Init.MemInc              = DMA_MINC_ENABLE;
    hdma_adc1.Init.PeriphDataAlignment = DMA_PDATAALIGN_HALFWORD;
    hdma_adc1.Init.MemDataAlignment    = DMA_MDATAALIGN_HALFWORD;
    hdma_adc1.Init.Mode                = DMA_NORMAL;
    hdma_adc1.Init.Priority            = DMA_PRIORITY_HIGH;
    hdma_adc1.Init.FIFOMode            = DMA_FIFOMODE_DISABLE;
    g_dbg_dma_init_status = (uint32_t)HAL_DMA_Init(&hdma_adc1);

    __HAL_LINKDMA(&hadc1, DMA_Handle, hdma_adc1);

    HAL_NVIC_SetPriority(DMA2_Stream0_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(DMA2_Stream0_IRQn);

    _module_initialized = 1;
}

uint8_t ADC_Capture_Start(uint32_t n_samples, uint32_t prescaler, uint32_t period)
{
    if (_capture_in_progress) return 0;
    _module_init();

    if (n_samples > ADCFAST_MAX_SAMPLES) n_samples = ADCFAST_MAX_SAMPLES;
    g_capture_n    = n_samples;
    g_capture_done = 0;
    _capture_in_progress = 1;

    __HAL_TIM_SET_PRESCALER(&htim1, prescaler);
    __HAL_TIM_SET_AUTORELOAD(&htim1, period);
    __HAL_TIM_SET_COUNTER(&htim1, 0);

    ADC_ChannelConfTypeDef sConfig = {0};
    sConfig.Channel      = ADC_CHANNEL_17;
    sConfig.Rank         = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_1CYCLE_5;
    sConfig.SingleDiff   = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber = ADC_OFFSET_NONE;
    sConfig.Offset       = 0;
    HAL_ADC_ConfigChannel(&hadc1, &sConfig);

    hadc1.Init.ExternalTrigConv     = ADC_EXTERNALTRIG_T1_TRGO2;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_RISING;
    /* Explicit rather than inherited from MX_ADC1_Init -- H7's HAL
     * exposes this as ConversionDataManagement, not the F1/F4-style
     * DMAContinuousRequests boolean. This is likely the REAL reason
     * both the TIM6 and TIM1 attempts timed out: if this was left at
     * its inherited ADC_CONVERSIONDATA_DR (register-only, matching
     * the original polling-based ADC_ReadVoltage() which never used
     * DMA), every conversion result went straight to the data
     * register and never reached DMA at all -- regardless of
     * whether the trigger itself fired correctly upstream.
     * ONESHOT matches our bounded, Normal-mode (non-circular) DMA
     * transfer of exactly n_samples. */
    hadc1.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DMA_ONESHOT;
    hadc1.Init.EOCSelection           = ADC_EOC_SINGLE_CONV;
    g_dbg_adc_init_status = (uint32_t)HAL_ADC_Init(&hadc1);

    g_dbg_adc_start_dma_status = (uint32_t)
        HAL_ADC_Start_DMA(&hadc1, (uint32_t *)g_adcfast_buf, n_samples);
    _capture_start_tick = HAL_GetTick();
    g_dbg_tim_start_status = (uint32_t)HAL_TIM_Base_Start(&htim1);

    return 1;
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    g_dbg_convcplt_fired_count++;   /* unconditional -- tells us if
                                        this callback fires AT ALL,
                                        even for the wrong instance */
    if (hadc->Instance != ADC1) return;

    HAL_TIM_Base_Stop(&htim1);
    HAL_ADC_Stop_DMA(&hadc1);

    hadc1.Init.ExternalTrigConv     = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    /* Also restore this -- set to DMA_ONESHOT for the capture, but
     * never reset. ADC_ReadVoltage()'s polling reads for OTHER
     * channels on hadc1 (PA2/PA3) depend on DR mode; leaving this at
     * DMA_ONESHOT after a capture is the likely cause of PA2/PA3
     * reading stale/identical values afterward. */
    hadc1.Init.ConversionDataManagement = ADC_CONVERSIONDATA_DR;
    HAL_ADC_Init(&hadc1);

    _capture_in_progress = 0;
    g_dbg_capture_elapsed_ms = HAL_GetTick() - _capture_start_tick;
    g_capture_done = 1;
}

/* HAL calls this automatically on ADC errors, including overrun (OVR) --
 * the failure mode where DMA can't drain a conversion before the next
 * one lands. Only a real risk at high trigger rates near the ADC's
 * physical ceiling; harmless at the 10kSPS already validated. */
void HAL_ADC_ErrorCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        g_dbg_adc_error_count++;
    }
}
