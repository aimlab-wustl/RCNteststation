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
 * dio.c
 * =============================================================*/

 #include "dio.h"

extern ADC_HandleTypeDef hadc1;
extern ADC_HandleTypeDef hadc2;

/* ── Pin lookup tables ───────────────────────────────────────────────────── */
static const uint16_t DIO_Pins[] = {
    DIO0_Pin,    /* index 0 = PD0  */
    DIO1_Pin,    /* index 1 = PD1  */
    DIO2_Pin,    /* index 2 = PD2  */
    DIO3_Pin,    /* index 3 = PD3  */
    DIO4_Pin,    /* index 4 = PD4  */
    DIO5_Pin,    /* index 5 = PD5  */
    DIO6_Pin,    /* index 6 = PD6  */
    DIO7_Pin,    /* index 7 = PD7  */
    DIO8_Pin,    /* index 8 = PD8  */
    DIO9_Pin,    /* index 9 = PD9  */
};

static const uint16_t PWM_Pins[] = {
    PWM_DIO12_Pin,   /* index 0 = PD12 */
    PWM_DIO13_Pin,   /* index 1 = PD13 */
    PWM_DIO14_Pin,   /* index 2 = PD14 */
    PWM_DIO15_Pin,   /* index 3 = PD15 */
};

/* Track direction state for switchable pins */
static DIO_Direction DIO89_Direction[2]   = { DIO_OUTPUT, DIO_OUTPUT };
static DIO_Direction DIO1215_Direction[4] = { DIO_OUTPUT, DIO_OUTPUT,
                                               DIO_OUTPUT, DIO_OUTPUT };

/* ── PD0-PD7: fixed outputs (read-back also works) ──────────────────────── */
void DIO_Write(uint8_t pin, uint8_t state)
{
    if (pin > 7) return;
    HAL_GPIO_WritePin(GPIOD, DIO_Pins[pin],
                      state ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

uint8_t DIO_Read(uint8_t pin)
{
    if (pin > 7) return 0;
    return (HAL_GPIO_ReadPin(GPIOD, DIO_Pins[pin]) == GPIO_PIN_SET) ? 1 : 0;
}

/* ── PD8-PD9: switchable direction ──────────────────────────────────────── */
void DIO_SetDirection(uint8_t pin, DIO_Direction dir)
{
    if (pin != 8 && pin != 9) return;
    uint8_t idx = pin - 8;

    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin  = DIO_Pins[pin];
    GPIO_InitStruct.Pull = GPIO_NOPULL;

    if (dir == DIO_OUTPUT)
    {
        GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    }
    else
    {
        GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    }

    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
    DIO89_Direction[idx] = dir;
}

void DIO_Write89(uint8_t pin, uint8_t state)
{
    if (pin != 8 && pin != 9) return;
    uint8_t idx = pin - 8;
    if (DIO89_Direction[idx] != DIO_OUTPUT) return;
    HAL_GPIO_WritePin(GPIOD, DIO_Pins[pin],
                      state ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

uint8_t DIO_Read89(uint8_t pin)
{
    if (pin != 8 && pin != 9) return 0;
    return (HAL_GPIO_ReadPin(GPIOD, DIO_Pins[pin]) == GPIO_PIN_SET) ? 1 : 0;
}

/* ── PD12-PD15: switchable direction + read ─────────────────────────────── */
void DIO_SetDirection1215(uint8_t pin, DIO_Direction dir)
{
    if (pin < 12 || pin > 15) return;
    uint8_t idx = pin - 12;

    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin  = PWM_Pins[idx];
    GPIO_InitStruct.Pull = GPIO_NOPULL;

    if (dir == DIO_OUTPUT)
    {
        GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    }
    else
    {
        GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    }

    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
    DIO1215_Direction[idx] = dir;
}

void DIO_WritePWM(uint8_t pin, uint8_t state)
{
    if (pin < 12 || pin > 15) return;
    uint8_t idx = pin - 12;
    if (DIO1215_Direction[idx] != DIO_OUTPUT) return;
    HAL_GPIO_WritePin(GPIOD, PWM_Pins[idx],
                      state ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

uint8_t DIO_ReadPWM(uint8_t pin)
{
    if (pin < 12 || pin > 15) return 0;
    return (HAL_GPIO_ReadPin(GPIOD, PWM_Pins[pin - 12]) == GPIO_PIN_SET) ? 1 : 0;
}

/* ── Onboard ADC PA1-PA4 ─────────────────────────────────────────────────── */
float ADC_ReadVoltage(uint8_t channel)
{
    if (channel < 1 || channel > 4) return 0.0f;

    ADC_ChannelConfTypeDef sConfig = {0};
    ADC_HandleTypeDef *hadc;
    uint32_t adc_channel;

    /* STM32H743 PA1-PA4 channel mapping:
       PA1 = ADC1_INP17
       PA2 = ADC1_INP14
       PA3 = ADC1_INP15
       PA4 = ADC2_INP18  */
    switch (channel)
    {
        case 1: hadc = &hadc1; adc_channel = ADC_CHANNEL_17; break;
        case 2: hadc = &hadc1; adc_channel = ADC_CHANNEL_14; break;
        case 3: hadc = &hadc1; adc_channel = ADC_CHANNEL_15; break;
        case 4: hadc = &hadc2; adc_channel = ADC_CHANNEL_18; break;
        default: return 0.0f;
    }

    sConfig.Channel      = adc_channel;
    sConfig.Rank         = ADC_REGULAR_RANK_1;
    sConfig.SamplingTime = ADC_SAMPLETIME_64CYCLES_5;
    sConfig.SingleDiff   = ADC_SINGLE_ENDED;
    sConfig.OffsetNumber = ADC_OFFSET_NONE;
    sConfig.Offset       = 0;
    sConfig.OffsetSignedSaturation = DISABLE;
    HAL_ADC_ConfigChannel(hadc, &sConfig);

    HAL_ADC_Start(hadc);
    HAL_ADC_PollForConversion(hadc, 10);
    uint32_t raw = HAL_ADC_GetValue(hadc);
    HAL_ADC_Stop(hadc);

    /* 16-bit ADC, 3.3V VREF */
    return ((float)raw / 65535.0f) * 3.3f;
}
