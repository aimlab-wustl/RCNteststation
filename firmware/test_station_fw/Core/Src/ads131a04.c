/* =============================================================
 * ads131a04.c — ADS131A04 24-bit ADC Driver with DMA streaming
 * AIMLAB_TESTSTATION_V3  /  STM32H743
 * =============================================================*/

#include "ads131a04.h"
#include <string.h>

extern SPI_HandleTypeDef hspi2;
extern DMA_HandleTypeDef hdma_spi2_rx;

/* ── Pin macros ──────────────────────────────────────────────── */
#define CS1_LOW()   HAL_GPIO_WritePin(ADC1_CS_GPIO_Port,  ADC1_CS_Pin,    GPIO_PIN_RESET)
#define CS1_HIGH()  HAL_GPIO_WritePin(ADC1_CS_GPIO_Port,  ADC1_CS_Pin,    GPIO_PIN_SET)
#define CS2_LOW()   HAL_GPIO_WritePin(ADC2_CS_GPIO_Port,  ADC2_CS_Pin,    GPIO_PIN_RESET)
#define CS2_HIGH()  HAL_GPIO_WritePin(ADC2_CS_GPIO_Port,  ADC2_CS_Pin,    GPIO_PIN_SET)
#define RESET_LOW()  HAL_GPIO_WritePin(ADC_RESET_GPIO_Port, ADC_RESET_Pin, GPIO_PIN_RESET)
#define RESET_HIGH() HAL_GPIO_WritePin(ADC_RESET_GPIO_Port, ADC_RESET_Pin, GPIO_PIN_SET)
#define DRDY1_READ() HAL_GPIO_ReadPin(ADC1_DRDY_GPIO_Port, ADC1_DRDY_Pin)
#define DRDY2_READ() HAL_GPIO_ReadPin(ADC2_DRDY_GPIO_Port, ADC2_DRDY_Pin)

#define SPI_TIMEOUT_MS  10
#define DRDY_TIMEOUT_MS 200

/* ================================================================
 * DMA ring buffer storage — placed in D2 SRAM (non-cacheable)
 * MPU Region 3 covers 0x30000000, 32KB, non-cacheable.
 * All DMA target buffers MUST be in this region.
 * ================================================================*/
__attribute__((section(".dma_buffers")))
uint8_t g_ads131_ring1[ADS131_RING_BUF_BYTES];

__attribute__((section(".dma_buffers")))
uint8_t g_ads131_ring2[ADS131_RING_BUF_BYTES];

__attribute__((section(".dma_buffers")))
uint8_t g_ads131_dma_buf1[ADS131_DMA_FRAME_BYTES];

__attribute__((section(".dma_buffers")))
uint8_t g_ads131_dma_buf2[ADS131_DMA_FRAME_BYTES];

volatile uint32_t g_ads131_ring1_head = 0;
volatile uint32_t g_ads131_ring1_tail = 0;
volatile uint32_t g_ads131_ring2_head = 0;
volatile uint32_t g_ads131_ring2_tail = 0;

volatile uint8_t g_ads131_dma_active_chip = 0;

/* Gate flag */
volatile uint8_t g_ads131_dma_stream_enabled = 0;
volatile uint8_t g_ads131_dma_stream_chip    = 1;  /* ← add this line */

/* Debug counters — readable via ADS_DBG command */
volatile uint32_t g_dbg_exti_count    = 0;   /* EXTI fired */
volatile uint32_t g_dbg_dma_start     = 0;   /* DMA started */
volatile uint32_t g_dbg_dma_complete  = 0;   /* DMA complete callback */
volatile uint32_t g_dbg_ring_written  = 0;   /* frame written to ring */

/* ── Internal helpers ────────────────────────────────────────── */
static inline void _cs_low(uint8_t chip)  { if (chip==1) CS1_LOW();  else CS2_LOW();  }
static inline void _cs_high(uint8_t chip) { if (chip==1) CS1_HIGH(); else CS2_HIGH(); }

static uint8_t _wait_drdy(uint8_t chip)
{
    uint32_t t0 = HAL_GetTick();
    while (HAL_GetTick() - t0 < DRDY_TIMEOUT_MS) {
        if (chip == 1) { if (DRDY1_READ() == GPIO_PIN_RESET) return 1; }
        else           { if (DRDY2_READ() == GPIO_PIN_RESET) return 1; }
    }
    return 0;
}

static uint32_t _spi_xfer24(uint8_t chip, uint32_t tx_word)
{
    (void)chip;
    uint8_t tx[3], rx[3] = {0,0,0};
    tx[0] = (tx_word >> 16) & 0xFF;
    tx[1] = (tx_word >>  8) & 0xFF;
    tx[2] = (tx_word >>  0) & 0xFF;
    HAL_SPI_TransmitReceive(&hspi2, tx, rx, 3, SPI_TIMEOUT_MS);
    return ((uint32_t)rx[0]<<16)|((uint32_t)rx[1]<<8)|rx[2];
}

static uint32_t _send_frame(uint8_t chip,
                             const uint32_t *tx, uint32_t *rx,
                             uint8_t n_words)
{
    _cs_low(chip);
    __NOP();__NOP();__NOP();__NOP();
    __NOP();__NOP();__NOP();__NOP();
    for (uint8_t i = 0; i < n_words; i++)
        rx[i] = _spi_xfer24(chip, tx ? tx[i] : 0);
    __NOP();__NOP();__NOP();__NOP();
    __NOP();__NOP();__NOP();__NOP();
    _cs_high(chip);
    __NOP();__NOP();__NOP();__NOP();
    return rx[0];
}

static float _raw_to_voltage(int32_t raw)
{
    return ((float)raw / 8388608.0f) * ADS131_VREF;
}

/* ================================================================
 * Public: HWReset, Init, SendCmd, WriteReg, ReadReg, SetOSR
 * (same as before — DMA added on top, not replacing these)
 * ================================================================*/
void ADS131A04_HWReset(void)
{
    CS1_HIGH(); CS2_HIGH();
    HAL_Delay(1);
    RESET_LOW();
    HAL_Delay(1);
    RESET_HIGH();
    HAL_Delay(5);
}

uint16_t ADS131A04_SendCmd(uint8_t chip, uint16_t cmd)
{
    uint32_t tx[1], rx[1];
    tx[0] = (uint32_t)cmd << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    return (uint16_t)(rx[0] >> 8);
}

uint8_t ADS131A04_WriteReg(uint8_t chip, uint8_t addr, uint8_t data)
{
    uint32_t tx[1], rx[1];
    uint16_t cmd = ADS131_CMD_WREG(addr, data);
    tx[0] = (uint32_t)cmd << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    return ((uint8_t)((rx[0]>>8)&0xFF) == data) ? 1 : 0;
}

uint8_t ADS131A04_ReadReg(uint8_t chip, uint8_t addr)
{
    uint32_t tx[1], rx[1];
    uint16_t cmd = ADS131_CMD_RREG(addr);
    tx[0] = (uint32_t)cmd << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    return (uint8_t)((rx[0]>>8)&0xFF);
}

uint8_t ADS131A04_Init(uint8_t chip, ADS131_OSR_t osr)
{
    uint32_t tx[1], rx[1];
    uint32_t t0 = HAL_GetTick();

    /* Poll for READY word */
    while (HAL_GetTick() - t0 < 50) {
        tx[0] = ADS131_CMD_NULL << 8;
        uint16_t status = (uint16_t)(_send_frame(chip, tx, rx, 1) >> 8);
        if (status == ADS131_STATUS_READY) break;
        HAL_Delay(1);
    }

    /* UNLOCK */
    tx[0] = (uint32_t)ADS131_CMD_UNLOCK << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    HAL_Delay(1);

    /* A_SYS_CFG: VREF_4V=1, HRM=1, INT_REFEN=1 → 0x78 */
    ADS131A04_WriteReg(chip, ADS131_REG_A_SYS_CFG, 0x78);
    HAL_Delay(300);   /* 4V reference settling time */

    /* CLK1: CLK_DIV=001 → fICLK=4MHz */
    ADS131A04_WriteReg(chip, ADS131_REG_CLK1, 0x02);

    /* CLK2: ICLK_DIV=001→÷2 fMOD=2MHz, OSR=caller */
    ADS131A04_WriteReg(chip, ADS131_REG_CLK2, (uint8_t)((0x01<<5)|(uint8_t)osr));

    /* ADC_ENA: all 4 channels */
    ADS131A04_WriteReg(chip, ADS131_REG_ADC_ENA, 0x0F);
    HAL_Delay(1);

    /* WAKEUP */
    tx[0] = (uint32_t)ADS131_CMD_WAKEUP << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    HAL_Delay(1);

    /* Discard 4 settling frames */
    for (int i = 0; i < 4; i++) {
        if (!_wait_drdy(chip)) return 0;
        uint32_t dummy_rx[5], dummy_tx[5] = {0,0,0,0,0};
        _send_frame(chip, dummy_tx, dummy_rx, 5);
    }
    return 1;
}

void ADS131A04_SetOSR(uint8_t chip, ADS131_OSR_t osr)
{
    uint32_t tx[1], rx[1];
    tx[0] = (uint32_t)ADS131_CMD_STANDBY << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    HAL_Delay(1);

    ADS131A04_WriteReg(chip, ADS131_REG_CLK2,
                       (uint8_t)((0x01<<5)|(uint8_t)osr));

    tx[0] = (uint32_t)ADS131_CMD_WAKEUP << 8;
    _send_frame(chip, tx, rx, 1);
    tx[0] = ADS131_CMD_NULL << 8;
    _send_frame(chip, tx, rx, 1);
    HAL_Delay(1);

    for (int i = 0; i < 4; i++) {
        if (!_wait_drdy(chip)) break;
        uint32_t dummy_rx[5], dummy_tx[5]={0,0,0,0,0};
        _send_frame(chip, dummy_tx, dummy_rx, 5);
    }
}

/* ================================================================
 * Blocking frame read — used for single reads, init, calibration
 * ================================================================*/
uint8_t ADS131A04_ReadFrame(uint8_t chip, ADS131_Frame_t *frame)
{
    if (!frame) return 0;
    memset(frame, 0, sizeof(ADS131_Frame_t));
    if (!_wait_drdy(chip)) return 0;

    uint32_t tx[5] = {0,0,0,0,0};
    uint32_t rx[5] = {0};
    _send_frame(chip, tx, rx, 5);

    frame->status = rx[0] >> 8;
    for (int ch = 0; ch < ADS131_NUM_CH; ch++) {
        uint32_t raw24 = rx[ch+1] & 0x00FFFFFF;
        frame->raw[ch] = (raw24 & 0x800000)
                         ? (int32_t)(raw24 | 0xFF000000)
                         : (int32_t)raw24;
        frame->voltage[ch] = _raw_to_voltage(frame->raw[ch]);
    }
    frame->valid = 1;
    return 1;
}

uint8_t ADS131A04_ReadBoth(ADS131_Frame_t *f1, ADS131_Frame_t *f2)
{
    return ADS131A04_ReadFrame(ADS131_CHIP1, f1) &
           ADS131A04_ReadFrame(ADS131_CHIP2, f2);
}

/* ================================================================
 * DMA streaming — EXTI triggers DMA, DMA complete fills ring buffer
 *
 * Flow:
 *   DRDY falls → EXTI9_5_IRQHandler → HAL_GPIO_EXTI_Callback
 *   → ADS131A04_DMA_StartChip(chip) → assert CS, HAL_SPI_Receive_DMA
 *   → DMA moves 15 bytes to g_ads131_dma_bufN
 *   → DMA1_Stream3_IRQHandler → HAL_SPI_RxCpltCallback
 *   → ADS131A04_DMA_RxComplete(chip) → deassert CS, copy to ring
 *
 * CMD_Task polls ADS131A04_RingAvailable() and drains the ring
 * buffer into CDC binary packets.
 * ================================================================*/

/* Called from HAL_GPIO_EXTI_Callback */
void ADS131A04_DMA_StartChip(uint8_t chip)
{
    g_dbg_exti_count++;
    if (!g_ads131_dma_stream_enabled) return;
    if (chip != g_ads131_dma_stream_chip) return;
    if (g_ads131_dma_active_chip != 0) return;

    /* If SPI is stuck in a busy state from previous blocking transfers,
     * force it back to READY so HAL_SPI_Receive_DMA can proceed.      */
    if (hspi2.State != HAL_SPI_STATE_READY)
        hspi2.State = HAL_SPI_STATE_READY;

    g_ads131_dma_active_chip = chip;
    uint8_t *dma_buf = (chip == 1) ? g_ads131_dma_buf1 : g_ads131_dma_buf2;

    _cs_low(chip);
    HAL_StatusTypeDef r = HAL_SPI_Receive_DMA(&hspi2, dma_buf, ADS131_DMA_FRAME_BYTES);
    if (r == HAL_OK) {
        g_dbg_dma_start++;
    } else {
        _cs_high(chip);                /* deassert CS on failure */
        g_ads131_dma_active_chip = 0;
    }
}

/* Called from HAL_SPI_RxCpltCallback */
void ADS131A04_DMA_RxComplete(uint8_t chip)
{
    g_dbg_dma_complete++;

    _cs_high(chip);

    uint8_t *dma_buf  = (chip == 1) ? g_ads131_dma_buf1  : g_ads131_dma_buf2;
    uint8_t *ring     = (chip == 1) ? g_ads131_ring1      : g_ads131_ring2;
    volatile uint32_t *head = (chip == 1) ? &g_ads131_ring1_head : &g_ads131_ring2_head;
    volatile uint32_t *tail = (chip == 1) ? &g_ads131_ring1_tail : &g_ads131_ring2_tail;

    uint32_t next_head = (*head + 1) % ADS131_RING_SLOTS;
    if (next_head != *tail)
    {
        memcpy(&ring[(*head) * ADS131_DMA_FRAME_BYTES],
               dma_buf,
               ADS131_DMA_FRAME_BYTES);
        *head = next_head;
        g_dbg_ring_written++;
    }

    g_ads131_dma_active_chip = 0;
}

/* Ring buffer query and pop — called from CMD_Task */
uint32_t ADS131A04_RingAvailable(uint8_t chip)
{
    volatile uint32_t h = (chip==1) ? g_ads131_ring1_head : g_ads131_ring2_head;
    volatile uint32_t t = (chip==1) ? g_ads131_ring1_tail : g_ads131_ring2_tail;
    return (h - t + ADS131_RING_SLOTS) % ADS131_RING_SLOTS;
}

uint8_t ADS131A04_RingPop(uint8_t chip, uint8_t *dst)
{
    uint8_t *ring     = (chip==1) ? g_ads131_ring1 : g_ads131_ring2;
    volatile uint32_t *head = (chip==1) ? &g_ads131_ring1_head : &g_ads131_ring2_head;
    volatile uint32_t *tail = (chip==1) ? &g_ads131_ring1_tail : &g_ads131_ring2_tail;

    if (*head == *tail) return 0;  /* empty */
    memcpy(dst, &ring[(*tail) * ADS131_DMA_FRAME_BYTES], ADS131_DMA_FRAME_BYTES);
    *tail = (*tail + 1) % ADS131_RING_SLOTS;
    return 1;
}

/* ================================================================
 * HAL callbacks — placed here so they're self-contained
 * ================================================================*/

/* EXTI callback — fired by HAL for each DRDY pin */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == ADC1_DRDY_Pin)
        ADS131A04_DMA_StartChip(ADS131_CHIP1);
    else if (GPIO_Pin == ADC2_DRDY_Pin)
        ADS131A04_DMA_StartChip(ADS131_CHIP2);
}

/* DMA RX complete callback — fired by HAL after 15 bytes received */
void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi)
{
    if (hspi->Instance == SPI2)
        ADS131A04_DMA_RxComplete(g_ads131_dma_active_chip);
}
