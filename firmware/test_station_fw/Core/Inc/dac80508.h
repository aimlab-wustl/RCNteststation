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
 * dac80508.h
 * =============================================================*/

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
