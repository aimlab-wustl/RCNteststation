/*
 * dac80508.h
 *
 *  Created on: Jun 1, 2026
 *      Author: samka
 */

#ifndef INC_DAC80508_H_
#define INC_DAC80508_H_

#include "main.h"

/* ── Hardware config ─────────────────────────────── */
#define DAC_NUM_CHIPS       5
#define DAC_NUM_CHANNELS    8

/* ── Register addresses ──────────────────────────── */
#define DAC80508_REG_NOP        0x00
#define DAC80508_REG_SYNC       0x02
#define DAC80508_REG_CONFIG     0x03
#define DAC80508_REG_GAIN       0x04
#define DAC80508_REG_TRIGGER    0x05
#define DAC80508_REG_DAC0       0x08  /* DAC0..DAC7 = 0x08..0x0F */

/* ── GAIN register value ─────────────────────────── */
/* REFDIV-EN=0, all channel gains=2 → 0..5V output range */
#define DAC80508_GAIN_2X        0x00FF

/* ── Public API ──────────────────────────────────── */
/* chip:    1..5  (1 = closest to MCU SDI pin)        */
/* channel: 1..8  (1 = OUT0, 8 = OUT7)                */
void DAC80508_Init(void);
void DAC80508_SetChannel(uint8_t chip, uint8_t channel, uint16_t code);
void DAC80508_SetVoltage(uint8_t chip, uint8_t channel, float voltage);
void DAC80508_ClearAll(void);

#endif /* INC_DAC80508_H_ */
