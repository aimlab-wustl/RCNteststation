/*
 * dac80508.c
 *
 *  Created on: Jun 1, 2026
 *      Author: samka
 */
#include "dac80508.h"

/* ── Timing ──────────────────────────────────────────────────────────────── */
/* 50 NOPs @ 480MHz ≈ 100ns per phase → ~3MHz effective SPI clock            */
/* Increased from 10 NOPs to give setup/hold margin for longer daisy chain   */
/* If DAC3-5 still fail, increase to 100 NOPs                                */
#define DAC_NOP()   do { \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
    __NOP(); __NOP(); __NOP(); __NOP(); __NOP(); \
} while(0)

/* ── Pin macros ──────────────────────────────────────────────────────────── */
#define DAC_CS_LOW()   HAL_GPIO_WritePin(GPIOE, DAC_CSn_Pin, GPIO_PIN_RESET)
#define DAC_CS_HIGH()  HAL_GPIO_WritePin(GPIOE, DAC_CSn_Pin, GPIO_PIN_SET)
#define DAC_SCK_LOW()  HAL_GPIO_WritePin(GPIOE, DAC_SCK_Pin, GPIO_PIN_RESET)
#define DAC_SCK_HIGH() HAL_GPIO_WritePin(GPIOE, DAC_SCK_Pin, GPIO_PIN_SET)
#define DAC_SDI_LOW()  HAL_GPIO_WritePin(GPIOE, DAC_SDI_Pin, GPIO_PIN_RESET)
#define DAC_SDI_HIGH() HAL_GPIO_WritePin(GPIOE, DAC_SDI_Pin, GPIO_PIN_SET)

/* ── Internal: build 24-bit frame ────────────────────────────────────────── */
/* DAC80508 frame:                                                             */
/*   bit23     = R/W (0=write)                                                */
/*   bits22:20 = 000                                                          */
/*   bits19:16 = register address                                             */
/*   bits15:0  = data                                                         */
static uint32_t DAC_BuildFrame(uint8_t reg, uint16_t data)
{
    return ((uint32_t)(reg & 0x0F) << 16) | (uint32_t)data;
}


#define DAC_BIT_DELAY_US    50U
static inline void DAC_DelayUs(uint32_t us)
{
    /* At 480MHz, ~480 cycles per microsecond */
    volatile uint32_t count = us * 120;  /* ~4 cycles per iteration */
    while(count--);
}
/* ── Internal: clock out one 24-bit frame on the SPI bus ─────────────────── */
/* DAC80508 SPI: CPOL=0, CPHA=1 — SDI sampled on FALLING edge of SCK         */
static void DAC_ShiftOut24(uint32_t frame)
{
    for (int i = 23; i >= 0; i--)
    {
        if (frame & (1UL << i))
            DAC_SDI_HIGH();
        else
            DAC_SDI_LOW();

        DAC_DelayUs(DAC_BIT_DELAY_US);
        DAC_SCK_HIGH();
        DAC_DelayUs(DAC_BIT_DELAY_US);
        DAC_SCK_LOW();
        DAC_DelayUs(DAC_BIT_DELAY_US);
    }
}

/* ── Internal: broadcast same frame to all 5 chips ──────────────────────── */
static void DAC_SendAll(uint8_t reg, uint16_t data)
{
    uint32_t frame = DAC_BuildFrame(reg, data);

    DAC_CS_LOW();
    HAL_Delay(1);        // ← replaces DAC_NOP()

    for (int chip = 0; chip < DAC_NUM_CHIPS; chip++)
        DAC_ShiftOut24(frame);

    HAL_Delay(1);        // ← replaces DAC_NOP()
    DAC_CS_HIGH();
    HAL_Delay(1);        // ← replaces DAC_NOP()
}

static void DAC_SendOne(uint8_t chip, uint8_t reg, uint16_t data)
{
    if (chip < 1 || chip > DAC_NUM_CHIPS) return;

    uint32_t frame     = DAC_BuildFrame(reg, data);
    uint32_t nop_frame = DAC_BuildFrame(DAC80508_REG_NOP, 0x0000);

    DAC_CS_LOW();
    HAL_Delay(1);

    uint8_t phys = (DAC_NUM_CHIPS + 1) - chip;   // chip1→5, chip2→4, chip3→3 ...

    for (int i = 0; i < (phys - 1); i++)
        DAC_ShiftOut24(nop_frame);

    DAC_ShiftOut24(frame);

    for (int i = 0; i < (DAC_NUM_CHIPS - phys); i++)
        DAC_ShiftOut24(nop_frame);

    HAL_Delay(1);
    DAC_CS_HIGH();
    HAL_Delay(1);
}

/* ── Public: initialise all 5 DAC80508 chips ────────────────────────────── */
void DAC80508_Init(void)
{
    /* Idle state: CS high, SCK low, SDI low */
    DAC_CS_HIGH();
    DAC_SCK_LOW();
    DAC_SDI_LOW();
    HAL_Delay(1);

    /* Software reset — TRIGGER register, SOFT-RESET = 0x000A */
    DAC_SendAll(DAC80508_REG_TRIGGER, 0x000A);
    HAL_Delay(20);

    /* CONFIG = 0x0000: internal ref active, all DACs powered, CRC off */
    DAC_SendAll(DAC80508_REG_CONFIG, 0x0000);
    HAL_Delay(2);

    /* SYNC = 0x0000: async update, output updates on CS rising edge */
    DAC_SendAll(DAC80508_REG_SYNC, 0x0000);
    HAL_Delay(2);

    /* GAIN = 0x00FF: gain=2 all channels, ref divider off → 0..5V */
    DAC_SendAll(DAC80508_REG_GAIN, DAC80508_GAIN_2X);
    HAL_Delay(2);

    /* Clear all outputs to 0V */
    DAC80508_ClearAll();
}

/* ── Public: set one channel by raw 16-bit code ─────────────────────────── */
/* chip: 1..5, channel: 1..8, code: 0x0000=0V 0xFFFF=5V                     */
void DAC80508_SetChannel(uint8_t chip, uint8_t channel, uint16_t code)
{
    if (chip < 1 || chip > DAC_NUM_CHIPS) return;
    if (channel < 1 || channel > DAC_NUM_CHANNELS) return;
    uint8_t reg = DAC80508_REG_DAC0 + (channel - 1);
    DAC_SendOne(chip, reg, code);
}

/* ── Public: set one channel by voltage ─────────────────────────────────── */
/* chip: 1..5, channel: 1..8, voltage: 0.0..5.0V                            */
void DAC80508_SetVoltage(uint8_t chip, uint8_t channel, float voltage)
{
    if (voltage < 0.0f) voltage = 0.0f;
    if (voltage > 5.0f) voltage = 5.0f;
    uint16_t code = (uint16_t)((voltage / 5.0f) * 65535.0f);
    DAC80508_SetChannel(chip, channel, code);
}

/* ── Public: clear all outputs on all chips to 0V ───────────────────────── */
void DAC80508_ClearAll(void)
{
    for (uint8_t ch = 0; ch < DAC_NUM_CHANNELS; ch++)
    {
        DAC_SendAll(DAC80508_REG_DAC0 + ch, 0x0000);
        HAL_Delay(1);
    }
}
