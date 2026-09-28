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
 * dio.h
 * =============================================================*/

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
