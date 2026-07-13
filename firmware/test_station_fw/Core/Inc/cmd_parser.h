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
