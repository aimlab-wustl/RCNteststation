/*
 * dio.h
 *
 *  Created on: Jun 1, 2026
 *      Author: samka
 */

#ifndef INC_DIO_H_
#define INC_DIO_H_

#include "main.h"

/* ── Direction type ──────────────────────────────── */
typedef enum {
    DIO_INPUT  = 0,
    DIO_OUTPUT = 1
} DIO_Direction;

/* ── Public API — Fixed outputs PD0-PD7 ─────────── */
/* pin: 0..7                                          */
void    DIO_Write(uint8_t pin, uint8_t state);
uint8_t DIO_Read(uint8_t pin);

/* ── Public API — Switchable PD8-PD9 ────────────── */
/* pin: 8 or 9                                        */
void    DIO_SetDirection(uint8_t pin, DIO_Direction dir);
void    DIO_Write89(uint8_t pin, uint8_t state);
uint8_t DIO_Read89(uint8_t pin);

/* ── Public API — PD12-PD15 ─────────────────────── */
/* pin: 12..15                                        */
/* Direction defaults to OUTPUT after MX_GPIO_Init.  */
/* Call DIO_SetDirection1215 to switch to INPUT.      */
void    DIO_SetDirection1215(uint8_t pin, DIO_Direction dir);
void    DIO_WritePWM(uint8_t pin, uint8_t state);
uint8_t DIO_ReadPWM(uint8_t pin);

/* ── Public API — Onboard ADC PA1-PA4 ───────────── */
/* channel: 1..4 → PA1..PA4                          */
/* returns voltage in float 0.0..3.3V                */
float ADC_ReadVoltage(uint8_t channel);

#endif /* INC_DIO_H_ */
