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
 * cmd_parser.h — USB CDC ASCII Command Parser
 * AIMLAB_TESTSTATION_V3  /  STM32H743
 *
 * Protocol — all ASCII, \n terminated:
 *   Host → MCU :  COMMAND [ARG1] [ARG2]\n
 *   MCU  → Host :  OK:...\r\n  |  ERR:...\r\n  |  DATA:...\r\n
 * =============================================================*/

#ifndef CMD_PARSER_H
#define CMD_PARSER_H

#include <stdint.h>

/* ── Configuration ─────────────────────────────────────────── */
#define CMD_BUF_SIZE                128
#define CMD_RESP_SIZE               512
#define FIRMWARE_VERSION            "AIMLAB_TESTSTATION_V3_r1"
#define STMADC_STREAM_INTERVAL_MS   1
#define ADS_DMA_PKT_FRAMES          32

/* ── Public API ────────────────────────────────────────────── */
void CMD_Feed(const uint8_t *buf, uint32_t len);
void CMD_Task(void);
void CMD_Send(const char *fmt, ...);

#endif /* CMD_PARSER_H */
