/* =============================================================
 * ads131a04.h — ADS131A04 24-bit ADC Driver with DMA streaming
 * AIMLAB_TESTSTATION_V3  /  STM32H743
 *
 * Hardware:
 *   SPI2:  PB13=SCLK, PB14=MISO (shared DOUT), PB15=MOSI (DIN)
 *   ADC1:  CS=PE1, DRDY=PE2
 *   ADC2:  CS=PE0, DRDY=PE3
 *   RESET: PE4 (shared)
 *   MCLK:  PA8 = MCO1 = 8MHz
 *
 * M-pin strapping:
 *   M0=IOVDD → async interrupt mode
 *   M1=GND   → 24-bit word length
 *   M2=GND   → Hamming OFF, CRC OFF
 *
 * Frame: [Status 24b][CH1 24b][CH2 24b][CH3 24b][CH4 24b] = 15 bytes
 *
 * Clock: fCLKIN=8MHz → CLK1 ÷2 → fICLK=4MHz → CLK2 ÷2 → fMOD=2MHz
 *   OSR_400 → 5kSPS (default)   OSR_32 → 62.5kSPS (max)
 *
 * DMA streaming:
 *   DRDY falling edge → EXTI → start SPI2 DMA RX (15 bytes)
 *   DMA complete → HAL_SPI_RxCpltCallback → store frame in ring buffer
 *   CMD_Task checks ring buffer → sends binary block over CDC
 *   Python: struct.unpack → numpy array → voltages
 *
 * Reference: AVDD=5V AVSS=GND, VREF_4V=1 → 4.0V internal ref
 *   Range: ±4.0V differential, 0–4V single-ended (AINxN=GND)
 *   1 LSB = (2×4.0V)/2^24 = 476nV
 * =============================================================*/

#ifndef INC_ADS131A04_H_
#define INC_ADS131A04_H_

#include "main.h"
#include <stdint.h>

/* ── Chip identifiers ────────────────────────────────────────── */
#define ADS131_CHIP1    1
#define ADS131_CHIP2    2
#define ADS131_NUM_CH   4

/* ── Reference voltage ───────────────────────────────────────── */
/* VREF_4V=1, AVDD=5V AVSS=GND → 4.0V                          */
#define ADS131_VREF     4.0f

/* ── Register addresses ──────────────────────────────────────── */
#define ADS131_REG_ID_MSB       0x00
#define ADS131_REG_ID_LSB       0x01
#define ADS131_REG_STAT_1       0x02
#define ADS131_REG_STAT_P       0x03
#define ADS131_REG_STAT_N       0x04
#define ADS131_REG_STAT_S       0x05
#define ADS131_REG_ERROR_CNT    0x06
#define ADS131_REG_STAT_M2      0x07
#define ADS131_REG_A_SYS_CFG    0x0B
#define ADS131_REG_D_SYS_CFG    0x0C
#define ADS131_REG_CLK1         0x0D
#define ADS131_REG_CLK2         0x0E
#define ADS131_REG_ADC_ENA      0x0F
#define ADS131_REG_ADC1         0x11
#define ADS131_REG_ADC2         0x12
#define ADS131_REG_ADC3         0x13
#define ADS131_REG_ADC4         0x14

/* ── SPI Commands ────────────────────────────────────────────── */
#define ADS131_CMD_NULL         0x0000
#define ADS131_CMD_RESET        0x0011
#define ADS131_CMD_STANDBY      0x0022
#define ADS131_CMD_WAKEUP       0x0033
#define ADS131_CMD_LOCK         0x0555
#define ADS131_CMD_UNLOCK       0x0655
#define ADS131_CMD_RREG(a)      (0x2000 | ((uint16_t)(a) << 8))
#define ADS131_CMD_WREG(a,d)    (0x4000 | ((uint16_t)(a) << 8) | (uint8_t)(d))

#define ADS131_STATUS_READY     0xFF04

/* ── OSR settings ────────────────────────────────────────────── */
typedef enum {
    ADS131_OSR_4096 = 0x00,   /* 0.5 kSPS  at fMOD=2MHz */
    ADS131_OSR_2048 = 0x01,   /* 1.0 kSPS              */
    ADS131_OSR_1024 = 0x02,   /* 2.0 kSPS              */
    ADS131_OSR_512  = 0x05,   /* 4.0 kSPS              */
    ADS131_OSR_400  = 0x06,   /* 5.0 kSPS  ← default   */
    ADS131_OSR_256  = 0x08,   /* 8.0 kSPS              */
    ADS131_OSR_128  = 0x0B,   /* 16.0 kSPS             */
    ADS131_OSR_64   = 0x0D,   /* 32.0 kSPS             */
    ADS131_OSR_32   = 0x0F,   /* 62.5 kSPS ← max       */
} ADS131_OSR_t;

/* ── Frame result ────────────────────────────────────────────── */
typedef struct {
    float    voltage[ADS131_NUM_CH];
    int32_t  raw[ADS131_NUM_CH];
    uint32_t status;
    uint8_t  valid;
} ADS131_Frame_t;

/* ── DMA ring buffer ─────────────────────────────────────────── */
/* Stores raw 15-byte SPI frames before processing.
 * One slot = 15 bytes (5 × 24-bit words per frame).
 * 256 slots = 3840 bytes — fits in D2 SRAM non-cacheable region.
 * At 62.5kSPS each slot holds ~16µs of data.                   */
#define ADS131_DMA_FRAME_BYTES  15
#define ADS131_RING_SLOTS       256
#define ADS131_RING_BUF_BYTES   (ADS131_DMA_FRAME_BYTES * ADS131_RING_SLOTS)

/* Placed in D2 SRAM (non-cacheable MPU region 3 at 0x30000000) */
/* Two buffers: one per chip                                     */
extern uint8_t g_ads131_ring1[ADS131_RING_BUF_BYTES];
extern uint8_t g_ads131_ring2[ADS131_RING_BUF_BYTES];
extern volatile uint32_t g_ads131_ring1_head;  /* written by ISR */
extern volatile uint32_t g_ads131_ring1_tail;  /* read by CMD_Task */
extern volatile uint32_t g_ads131_ring2_head;
extern volatile uint32_t g_ads131_ring2_tail;

/* DMA receive buffer — one frame at a time, in non-cacheable RAM */
extern uint8_t g_ads131_dma_buf1[ADS131_DMA_FRAME_BYTES];
extern uint8_t g_ads131_dma_buf2[ADS131_DMA_FRAME_BYTES];

/* Which chip is currently being read by DMA */
extern volatile uint8_t  g_ads131_dma_active_chip;
extern volatile uint8_t  g_ads131_dma_stream_enabled;
extern volatile uint8_t  g_ads131_dma_stream_chip;

/* Debug counters — read via ADS_DBG command to trace DMA chain */
extern volatile uint32_t g_dbg_exti_count;
extern volatile uint32_t g_dbg_dma_start;
extern volatile uint32_t g_dbg_dma_complete;
extern volatile uint32_t g_dbg_ring_written;

/* ── Public API ──────────────────────────────────────────────── */
void    ADS131A04_HWReset(void);
uint8_t ADS131A04_Init(uint8_t chip, ADS131_OSR_t osr);
uint8_t ADS131A04_ReadFrame(uint8_t chip, ADS131_Frame_t *frame);
uint8_t ADS131A04_ReadBoth(ADS131_Frame_t *f1, ADS131_Frame_t *f2);
uint8_t ADS131A04_WriteReg(uint8_t chip, uint8_t addr, uint8_t data);
uint8_t ADS131A04_ReadReg(uint8_t chip, uint8_t addr);
void    ADS131A04_SetOSR(uint8_t chip, ADS131_OSR_t osr);
uint16_t ADS131A04_SendCmd(uint8_t chip, uint16_t cmd);

/* DMA streaming control */
void    ADS131A04_DMA_StartChip(uint8_t chip);   /* called from EXTI ISR */
void    ADS131A04_DMA_RxComplete(uint8_t chip);  /* called from DMA ISR  */
uint32_t ADS131A04_RingAvailable(uint8_t chip);  /* frames ready to read */
uint8_t  ADS131A04_RingPop(uint8_t chip, uint8_t *dst_15bytes); /* get one frame */

#endif /* INC_ADS131A04_H_ */
