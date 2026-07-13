/* =============================================================
 * cmd_parser.c — USB CDC ASCII Command Parser  (REVISED v3)
 * AIMLAB_TESTSTATION_ADC_V1  /  STM32H743
 *
 * v2 fixes:
 *   1. No HAL_Delay() inside CMD_Send — safe from ISR context
 *   2. ISR-safe pending-flag dispatch via CMD_Task (main loop)
 *   3. D-Cache safe buffer copy in CMD_Feed
 *   4. strtok replaced with manual _next_token (reentrant-safe)
 *   5. HAL_GetTick() for stream timing (ISR-safe on H7)
 *
 * v3 fix:
 *   6. CMD_Send now spins on TxState instead of HAL_Delay(1).
 *      Removes the 1ms floor that was capping streaming at 1kSPS.
 *      Expected throughput: 5,000-8,000 SPS over CDC.
 * =============================================================*/

#include "cmd_parser.h"
#include "dio.h"
#include "dac80508.h"
#include "usbd_cdc_if.h"
#include "usbd_cdc.h"       /* USBD_CDC_HandleTypeDef */
#include "ads131a04.h"
#include "tia.h"
#include "stm_adc.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>


/* USB device handle — defined in usb_device.c */
extern USBD_HandleTypeDef hUsbDeviceFS;

/* ================================================================
 * Internal state
 * ================================================================*/

/* Line accumulator — filled from ISR via CMD_Feed */
static volatile uint8_t  _rx_buf[CMD_BUF_SIZE];
static volatile uint32_t _rx_len   = 0;

/* Pending command flag — set by CMD_Feed (ISR), cleared by CMD_Task (main) */
static volatile uint8_t  _cmd_pending = 0;

/* Working copy of the command line — used only in CMD_Task (main context) */
static char _work_buf[CMD_BUF_SIZE];

/* TX response buffer — only written in CMD_Task / command handlers */
static char _resp_buf[CMD_RESP_SIZE];

/* Stream state */
static uint8_t  _stream_active  = 0;
static uint8_t  _stream_channel = 1;   /* 1-4 or 0=ALL */
static uint32_t _stream_total   = 0;   /* 0 = indefinite */
static uint32_t _stream_sent    = 0;
static uint32_t _stream_last_ms = 0;

/* ── ADS stream state ────────────────────────────────────────── */
static uint8_t  _ads_stream_active = 0;
static uint8_t  _ads_stream_chip   = 1;
static uint32_t _ads_stream_total  = 0;
static uint32_t _ads_stream_sent   = 0;

/* ── ADS DMA binary stream state ────────────────────────────── */
/* Binary packet format per CDC send:                            */
/*   [0]   = 'D' (0x44) binary marker                           */
/*   [1]   = chip number                                         */
/*   [2-5] = frame counter (uint32 big-endian)                  */
/*   [6:]  = N × 15 raw SPI bytes                               */
static uint8_t  _ads_dma_active = 0;
static uint8_t  _ads_dma_chip   = 1;
static uint32_t _ads_dma_total  = 0;   /* 0 = indefinite */
static uint32_t _ads_dma_sent   = 0;



/* ================================================================
 * CMD_Send — safe TX, called only from main-loop context
 * Retries if USB stack is busy (e.g. during streaming).
 * ================================================================*/
void CMD_Send(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(_resp_buf, sizeof(_resp_buf) - 3, fmt, args);
    va_end(args);

    if (n < 0) n = 0;
    if (n > (int)(sizeof(_resp_buf) - 3)) n = (int)(sizeof(_resp_buf) - 3);

    _resp_buf[n]     = '\r';
    _resp_buf[n + 1] = '\n';
    _resp_buf[n + 2] = '\0';
    uint16_t total = (uint16_t)(n + 2);

    /* Wait for USB TX to be free — spin on TxState rather than HAL_Delay.
     * HAL_Delay(1) was capping throughput at 1kSPS.
     * TxState clears in ~125µs (USB FS full-speed packet time) so
     * a spin loop here costs almost nothing and removes the 1ms floor.
     * Hard timeout at 5ms prevents hang if USB disconnects mid-stream. */
    USBD_CDC_HandleTypeDef *hcdc =
        (USBD_CDC_HandleTypeDef *)hUsbDeviceFS.pClassData;

    uint32_t deadline = HAL_GetTick() + 5;   /* 5ms absolute timeout */
    while (hcdc->TxState != 0)
    {
        if (HAL_GetTick() >= deadline)
            return;   /* USB disconnected or stalled — drop silently */
    }

    CDC_Transmit_FS((uint8_t *)_resp_buf, total);
}

/* ================================================================
 * CMD_Feed — called from CDC_Receive_FS (USB ISR context)
 * MUST be fast: copy bytes, set flag, return immediately.
 * All parsing happens in CMD_Task (main loop).
 * ================================================================*/
void CMD_Feed(const uint8_t *buf, uint32_t len)
{
    for (uint32_t i = 0; i < len; i++)
    {
        uint8_t c = buf[i];
        if (c == '\r') continue;

        if (c == '\n')
        {
            /* Mark line as complete — CMD_Task will process it */
            if (_rx_len > 0 && !_cmd_pending)
            {
                _rx_buf[_rx_len] = '\0';
                _cmd_pending = 1;   /* signal main loop */
            }
            /* Don't reset _rx_len here — CMD_Task resets it after copy */
        }
        else
        {
            if (!_cmd_pending && _rx_len < CMD_BUF_SIZE - 1)
                _rx_buf[_rx_len++] = c;
        }
    }
}

/* ================================================================
 * Internal helpers (all called from main context only)
 * ================================================================*/

static char *_trim(char *s)
{
    while (isspace((unsigned char)*s)) s++;
    int len = (int)strlen(s);
    while (len > 0 && isspace((unsigned char)s[len - 1]))
        s[--len] = '\0';
    return s;
}

/* Split "CMD ARGS" at first space into cmd and args pointers */
static void _split_cmd(char *line, char **cmd_out, char **args_out)
{
    *cmd_out  = line;
    *args_out = NULL;
    char *sp = strchr(line, ' ');
    if (sp) {
        *sp      = '\0';
        *args_out = _trim(sp + 1);
    }
    /* Uppercase command name */
    for (char *p = *cmd_out; *p; p++)
        *p = (char)toupper((unsigned char)*p);
}

/* Safe integer/hex parse — returns 0 and sets *ok=0 on failure */
static uint32_t _parse_uint(const char *s, int *ok)
{
    if (!s || *s == '\0') { *ok = 0; return 0; }
    char *end;
    uint32_t v;
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
        v = (uint32_t)strtoul(s + 2, &end, 16);
    else
        v = (uint32_t)strtoul(s, &end, 10);
    *ok = (end != s && (*end == '\0' || isspace((unsigned char)*end)));
    return v;
}

/* Manual strtok replacement — does not modify string, returns next token */
static char *_next_token(char **cursor)
{
    if (!cursor || !*cursor) return NULL;
    char *p = *cursor;
    while (*p && isspace((unsigned char)*p)) p++;
    if (*p == '\0') { *cursor = p; return NULL; }
    char *start = p;
    while (*p && !isspace((unsigned char)*p)) p++;
    if (*p) { *p = '\0'; p++; }
    *cursor = p;
    return start;
}

/* ================================================================
 * Command handlers
 * ================================================================*/

static void _cmd_identify(char *args)
{
    (void)args;
    CMD_Send("OK:%s", FIRMWARE_VERSION);
}

static void _cmd_status(char *args)
{
    (void)args;
    /* Send as integer millivolts — avoids newlib-nano float printf issue */
    uint32_t v1 = (uint32_t)(ADC_ReadVoltage(1) * 10000.0f);
    uint32_t v2 = (uint32_t)(ADC_ReadVoltage(2) * 10000.0f);
    uint32_t v3 = (uint32_t)(ADC_ReadVoltage(3) * 10000.0f);
    uint32_t v4 = (uint32_t)(ADC_ReadVoltage(4) * 10000.0f);
    CMD_Send("OK:FW=%s,PA1=%lumV,PA2=%lumV,PA3=%lumV,PA4=%lumV,STREAM=%s",
             FIRMWARE_VERSION,
             (unsigned long)v1, (unsigned long)v2,
             (unsigned long)v3, (unsigned long)v4,
             _stream_active ? "ACTIVE" : "IDLE");
}

/* STMDIO_WRITE <hex>  — write bits 0-7 to PD0-PD7 */
static void _cmd_dio_write(char *args)
{
    if (!args || *args == '\0') {
        CMD_Send("ERR:STMDIO_WRITE needs hex e.g. 0x00FF");
        return;
    }
    int ok;
    uint32_t mask = _parse_uint(_trim(args), &ok);
    if (!ok) { CMD_Send("ERR:Bad value '%s'", args); return; }
    for (int p = 0; p <= 7; p++)
        DIO_Write(p, (mask >> p) & 1);
    CMD_Send("OK:DIO=0x%04X", (unsigned)(mask & 0xFF));
}

/* STMDIO_WRITE_PIN <pin> <0|1> */
static void _cmd_dio_write_pin(char *args)
{
    char *cur = args;
    char *s_pin   = _next_token(&cur);
    char *s_state = _next_token(&cur);
    if (!s_pin || !s_state) {
        CMD_Send("ERR:Usage: STMDIO_WRITE_PIN <pin> <0|1>");
        return;
    }
    int ok1, ok2;
    uint32_t pin   = _parse_uint(s_pin,   &ok1);
    uint32_t state = _parse_uint(s_state, &ok2);
    if (!ok1 || !ok2) { CMD_Send("ERR:Bad args"); return; }

    uint8_t s = (uint8_t)(state & 1);
    if      (pin <= 7)               DIO_Write((uint8_t)pin, s);
    else if (pin == 8 || pin == 9)   DIO_Write89((uint8_t)pin, s);
    else if (pin >= 12 && pin <= 15) DIO_WritePWM((uint8_t)pin, s);
    else { CMD_Send("ERR:Pin %d invalid (0-9,12-15)", (int)pin); return; }
    CMD_Send("OK:PIN%d=%d", (int)pin, (int)s);
}

/* STMDIO_READ — return all readable pins */
static void _cmd_dio_read(char *args)
{
    (void)args;
    uint8_t lo = 0;
    for (int p = 0; p <= 7; p++)
        lo |= (uint8_t)(DIO_Read(p) << p);
    uint8_t p8  = DIO_Read89(8);
    uint8_t p9  = DIO_Read89(9);
    uint8_t p12 = DIO_ReadPWM(12);
    uint8_t p13 = DIO_ReadPWM(13);
    uint8_t p14 = DIO_ReadPWM(14);
    uint8_t p15 = DIO_ReadPWM(15);
    CMD_Send("OK:PD0-7=0x%02X,PD8=%d,PD9=%d,PD12=%d,PD13=%d,PD14=%d,PD15=%d",
             (unsigned)lo, p8, p9, p12, p13, p14, p15);
}

/* STMDIO_READ_PIN <pin> */
static void _cmd_dio_read_pin(char *args)
{
    if (!args || *args == '\0') { CMD_Send("ERR:Missing pin"); return; }
    int ok;
    uint32_t pin = _parse_uint(_trim(args), &ok);
    if (!ok) { CMD_Send("ERR:Bad pin"); return; }
    uint8_t s = 0;
    if      (pin <= 7)                s = DIO_Read((uint8_t)pin);
    else if (pin == 8 || pin == 9)    s = DIO_Read89((uint8_t)pin);
    else if (pin >= 12 && pin <= 15)  s = DIO_ReadPWM((uint8_t)pin);
    else { CMD_Send("ERR:Pin %d not readable (valid: 0-9, 12-15)", (int)pin); return; }
    CMD_Send("OK:PIN%d=%d", (int)pin, (int)s);
}

/* STMDIO_DIR <pin> <IN|OUT>  — pin 8, 9, or 12-15 */
static void _cmd_dio_dir(char *args)
{
    char *cur = args;
    char *s_pin = _next_token(&cur);
    char *s_dir = _next_token(&cur);
    if (!s_pin || !s_dir) {
        CMD_Send("ERR:Usage: STMDIO_DIR <pin 8|9|12-15> <IN|OUT>");
        return;
    }
    int ok;
    uint32_t pin = _parse_uint(s_pin, &ok);
    if (!ok) { CMD_Send("ERR:Bad pin"); return; }

    /* Check pin is switchable */
    uint8_t valid = (pin == 8 || pin == 9 || (pin >= 12 && pin <= 15));
    if (!valid) {
        CMD_Send("ERR:Pin %d not switchable (valid: 8, 9, 12-15)", (int)pin);
        return;
    }

    /* Uppercase direction */
    for (char *p = s_dir; *p; p++) *p = (char)toupper((unsigned char)*p);

    DIO_Direction dir;
    if      (strcmp(s_dir, "IN")  == 0) dir = DIO_INPUT;
    else if (strcmp(s_dir, "OUT") == 0) dir = DIO_OUTPUT;
    else { CMD_Send("ERR:Direction must be IN or OUT"); return; }

    if (pin == 8 || pin == 9)
        DIO_SetDirection((uint8_t)pin, dir);
    else
        DIO_SetDirection1215((uint8_t)pin, dir);

    CMD_Send("OK:PIN%d_DIR=%s", (int)pin, s_dir);
}

/* DAC_SET <chip 1-5> <ch 1-8> <voltage 0-5> */
static void _cmd_dac_set(char *args)
{
    char *cur  = args;
    char *s_c  = _next_token(&cur);
    char *s_ch = _next_token(&cur);
    char *s_v  = _next_token(&cur);
    if (!s_c || !s_ch || !s_v) {
        CMD_Send("ERR:Usage: DAC_SET <chip 1-5> <ch 1-8> <V 0-5>");
        return;
    }
    int ok1, ok2;
    uint32_t chip = _parse_uint(s_c,  &ok1);
    uint32_t ch   = _parse_uint(s_ch, &ok2);
    float    volt = strtof(s_v, NULL);
    if (!ok1 || !ok2 || chip < 1 || chip > 5 || ch < 1 || ch > 8) {
        CMD_Send("ERR:chip 1-5, ch 1-8 required");
        return;
    }
    if (volt < 0.0f || volt > 5.0f) {
        CMD_Send("ERR:Voltage 0.0-5.0V");
        return;
    }
    DAC80508_SetVoltage((uint8_t)chip, (uint8_t)ch, volt);
    /* Send voltage as integer 0.1mV units */
    uint32_t v_int = (uint32_t)(volt * 10000.0f);
    CMD_Send("OK:DAC_C%d_CH%d=%lumV", (int)chip, (int)ch, (unsigned long)v_int);
}

/* DAC_SET_ALL <voltage> — all chips all channels */
static void _cmd_dac_set_all(char *args)
{
    if (!args || *args == '\0') {
        CMD_Send("ERR:Usage: DAC_SET_ALL <V 0-5>");
        return;
    }
    float volt = strtof(_trim(args), NULL);
    if (volt < 0.0f || volt > 5.0f) {
        CMD_Send("ERR:Voltage 0.0-5.0V");
        return;
    }
    for (uint8_t c = 1; c <= 5; c++)
        for (uint8_t ch = 1; ch <= 8; ch++)
            DAC80508_SetVoltage(c, ch, volt);
    uint32_t v_int = (uint32_t)(volt * 10000.0f);
    CMD_Send("OK:DAC_ALL=%lumV", (unsigned long)v_int);
}

/* DAC_CLEAR */
static void _cmd_dac_clear(char *args)
{
    (void)args;
    DAC80508_ClearAll();
    CMD_Send("OK:DAC_ALL=0.0000V");
}

/* STMADC <ch|ALL> — single shot
 * Sends values as integer 0.1mV units (10000 = 1.0000V)
 * Python divides by 10000.0 to get volts                */
static void _cmd_stmadc(char *args)
{
    if (!args || *args == '\0') {
        CMD_Send("ERR:Usage: STMADC <1-4|ALL>");
        return;
    }
    char *a = _trim(args);
    for (char *p = a; *p; p++) *p = (char)toupper((unsigned char)*p);

    if (strcmp(a, "ALL") == 0) {
        uint32_t v1 = (uint32_t)(ADC_ReadVoltage(1) * 10000.0f);
        uint32_t v2 = (uint32_t)(ADC_ReadVoltage(2) * 10000.0f);
        uint32_t v3 = (uint32_t)(ADC_ReadVoltage(3) * 10000.0f);
        uint32_t v4 = (uint32_t)(ADC_ReadVoltage(4) * 10000.0f);
        CMD_Send("DATA:ch1=%lu,ch2=%lu,ch3=%lu,ch4=%lu",
                 (unsigned long)v1,(unsigned long)v2,
                 (unsigned long)v3,(unsigned long)v4);
    } else {
        int ok;
        uint32_t ch = _parse_uint(a, &ok);
        if (!ok || ch < 1 || ch > 4) {
            CMD_Send("ERR:Channel must be 1-4 or ALL");
            return;
        }
        uint32_t v = (uint32_t)(ADC_ReadVoltage((uint8_t)ch) * 10000.0f);
        CMD_Send("DATA:ch%d=%lu", (int)ch, (unsigned long)v);
    }
}

/* STMADC_STREAM <ch> <n>  ch=1-4 or 0=ALL, n=0 indefinite */
static void _cmd_stmadc_stream(char *args)
{
    if (_stream_active) {
        CMD_Send("ERR:Stream active, send STMADC_STOP first");
        return;
    }
    char *cur  = args;
    char *s_ch = _next_token(&cur);
    char *s_n  = _next_token(&cur);
    if (!s_ch || !s_n) {
        CMD_Send("ERR:Usage: STMADC_STREAM <ch 0-4> <n>");
        return;
    }
    int ok1, ok2;
    uint32_t ch = _parse_uint(s_ch, &ok1);
    uint32_t n  = _parse_uint(s_n,  &ok2);
    if (!ok1 || !ok2 || ch > 4) {
        CMD_Send("ERR:ch 0(ALL)-4, n samples (0=infinite)");
        return;
    }
    _stream_channel = (uint8_t)ch;
    _stream_total   = n;
    _stream_sent    = 0;
    _stream_last_ms = HAL_GetTick();
    _stream_active  = 1;
    CMD_Send("OK:STREAM_START ch=%d n=%d", (int)ch, (int)n);
}

/* STMADC_STOP */
static void _cmd_stmadc_stop(char *args)
{
    (void)args;
    if (!_stream_active) {
        CMD_Send("ERR:No active stream");
        return;
    }
    _stream_active = 0;
    CMD_Send("OK:STREAM_STOP samples=%d", (int)_stream_sent);
}

static void _cmd_capture_step(char *args)
{
    char *cursor = args;
    int ok1, ok2, ok3, ok4;
    uint32_t n_samples    = _parse_uint(_next_token(&cursor), &ok1);
    uint32_t prescaler    = _parse_uint(_next_token(&cursor), &ok2);
    uint32_t period       = _parse_uint(_next_token(&cursor), &ok3);
    uint32_t pretrig_pct  = _parse_uint(_next_token(&cursor), &ok4);
    if (!ok4) pretrig_pct = 20;   /* default: capture 20% pre-step baseline */

    if (!ok1 || !ok2 || !ok3) {
        CMD_Send("ERR:Usage: CAPTURE_STEP n_samples prescaler period "
                 "[pretrig_pct]  (pretrig_pct default=20)");
        return;
    }
    if (n_samples > ADCFAST_MAX_SAMPLES) {
        CMD_Send("ERR:n_samples max is %d", ADCFAST_MAX_SAMPLES);
        return;
    }

    /* Ensure PD9 starts LOW before arming the capture, so the
     * pre-trigger baseline is a clean flat line. */
    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_RESET);
    HAL_Delay(1);   /* 1ms -- plenty for the output to settle */

    uint32_t pretrig_samples = (n_samples * pretrig_pct) / 100;

    /* Pre-arm DMA + ADC. Capture starts immediately on first TIM1 TRGO2. */
    if (!ADC_Capture_Start(n_samples, prescaler, period)) {
        CMD_Send("ERR:Capture already in progress");
        return;
    }

    /* Wait until exactly pretrig_samples have been captured, then fire
     * the step. Uses the DMA's own NDTR (Number of Data to Transfer)
     * register, which counts down in hardware as each sample lands --
     * far more precise than HAL_Delay() (1ms granularity) which was
     * causing the step to fire ~500us late at 3.2MSPS.
     *
     * DMA2_Stream0->NDTR starts at n_samples and counts DOWN to 0.
     * Samples captured so far = n_samples - NDTR.
     * We want to fire when captured >= pretrig_samples, i.e.
     * when NDTR <= (n_samples - pretrig_samples). */
    uint32_t ndtr_threshold = n_samples - pretrig_samples;
    uint32_t pre_deadline   = HAL_GetTick() + 3000;
    while (DMA2_Stream0->NDTR > ndtr_threshold) {
        if (HAL_GetTick() >= pre_deadline) {
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_RESET);
            CMD_Send("ERR:Pre-trigger wait timed out");
            return;
        }
    }

    /* Fire the step -- this now happens at precisely the right point
     * in the capture buffer, within one sample interval of pretrig_samples */
    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_SET);

    /* Wait for DMA to finish the remaining (100-pretrig)% of the buffer */
    uint32_t deadline = HAL_GetTick() + 3000;
    while (!g_capture_done) {
        if (HAL_GetTick() >= deadline) {
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_RESET);
            CMD_Send("ERR:Capture timed out");
            return;
        }
    }

    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_9, GPIO_PIN_RESET);

    /* Inform Python where in the buffer the step edge fired */
    CMD_Send("PRETRIG:%lu", (unsigned long)pretrig_samples);

    /* Send buffer */
    uint32_t n_bytes = g_capture_n * (uint32_t)sizeof(uint16_t);
    CMD_Send("BINARY:%lu", (unsigned long)n_bytes);

    uint32_t tx_deadline = HAL_GetTick() + 2000;
    while (CDC_Transmit_FS((uint8_t *)g_adcfast_buf,
                            (uint16_t)n_bytes) == USBD_BUSY) {
        if (HAL_GetTick() >= tx_deadline) {
            CMD_Send("ERR:CDC busy timeout");
            return;
        }
    }

    USBD_CDC_HandleTypeDef *hcdc =
        (USBD_CDC_HandleTypeDef *)hUsbDeviceFS.pClassData;
    uint32_t drain_deadline = HAL_GetTick() + 2000;
    while (hcdc->TxState != 0) {
        if (HAL_GetTick() >= drain_deadline) {
            CMD_Send("ERR:CDC drain timeout");
            return;
        }
    }

    CMD_Send("OK:CAPTURE_STEP_DONE n=%lu", (unsigned long)g_capture_n);
}



static void _cmd_adcfast_capture(char *args)
{
    char *cursor = args;
    int ok1, ok2, ok3;
    uint32_t n_samples  = _parse_uint(_next_token(&cursor), &ok1);
    uint32_t prescaler  = _parse_uint(_next_token(&cursor), &ok2);
    uint32_t period     = _parse_uint(_next_token(&cursor), &ok3);

    if (!ok1 || !ok2 || !ok3) {
        CMD_Send("ERR:Usage: ADCFAST_CAPTURE n_samples prescaler period "
                 "(try 1000 23 999 for 10kSPS)");
        return;
    }
    if (n_samples > ADCFAST_MAX_SAMPLES) {
        CMD_Send("ERR:n_samples max is %d", ADCFAST_MAX_SAMPLES);
        return;
    }

    if (!ADC_Capture_Start(n_samples, prescaler, period)) {
        CMD_Send("ERR:Capture already in progress");
        return;
    }

    /* Bounded wait -- a 1000-sample capture at 10kSPS takes ~100ms,
     * comfortably inside this timeout. Blocking here (main-loop/
     * CMD_Task context, NOT an ISR) is fine for now; revisit if
     * capture durations grow much longer than this. */
    uint32_t deadline = HAL_GetTick() + 3000;
    while (!g_capture_done) {
        if (HAL_GetTick() >= deadline) {
            CMD_Send("ERR:Capture timed out -- check TIM1/DMA2_Stream0 config");
            return;
        }
    }

    /* Single raw binary transfer -- NOT a loop of ASCII CMD_Send()
     * calls. An earlier looped-text version measured ~10.2s round
     * trip for 1000 samples, over 100x slower than the ~100ms
     * capture itself. One binary transfer avoids that entirely. */
    uint32_t n_bytes = g_capture_n * (uint32_t)sizeof(uint16_t);
    CMD_Send("BINARY:%lu", (unsigned long)n_bytes);

    uint32_t tx_deadline = HAL_GetTick() + 2000;
    while (CDC_Transmit_FS((uint8_t *)g_adcfast_buf, (uint16_t)n_bytes) == USBD_BUSY) {
        if (HAL_GetTick() >= tx_deadline) {
            CMD_Send("ERR:CDC busy timeout during binary transmit");
            return;
        }
    }

    /* CDC_Transmit_FS() returning "not busy" means this transfer was
     * successfully STARTED -- not that it has FINISHED. For large
     * payloads (confirmed: failed at 8000 samples/16KB, worked fine
     * at 2000 samples/4KB) the transfer is still draining over USB
     * when this next line would otherwise execute immediately after,
     * and the OK line below gets silently dropped instead of queued.
     * Wait for the driver's own TxState to confirm actual completion. */
    USBD_CDC_HandleTypeDef *hcdc = (USBD_CDC_HandleTypeDef *)hUsbDeviceFS.pClassData;
    uint32_t drain_deadline = HAL_GetTick() + 2000;
    while (hcdc->TxState != 0) {
        if (HAL_GetTick() >= drain_deadline) {
            CMD_Send("ERR:CDC transmit did not complete in time");
            return;
        }
    }

    CMD_Send("OK:ADCFAST_DONE n=%lu", (unsigned long)g_capture_n);
}

static void _cmd_adcfast_dbg(char *args)
{
    (void)args;
    CMD_Send("DATA:dma_init=%lu adc_init=%lu adc_start_dma=%lu "
             "tim_start=%lu convcplt_fired=%lu capture_done=%u "
             "elapsed_ms=%lu adc_errors=%lu",
             (unsigned long)g_dbg_dma_init_status,
             (unsigned long)g_dbg_adc_init_status,
             (unsigned long)g_dbg_adc_start_dma_status,
             (unsigned long)g_dbg_tim_start_status,
             (unsigned long)g_dbg_convcplt_fired_count,
             (unsigned)g_capture_done,
             (unsigned long)g_dbg_capture_elapsed_ms,
             (unsigned long)g_dbg_adc_error_count);
    CMD_Send("OK:ADCFAST_DBG_DONE");
}

/* ── ADS_READ <chip> [ch] ────────────────────────────────────── */
/* chip = 1 or 2, ch = 1-4 or omitted for all 4 channels        */
/* e.g. ADS_READ 1      → all 4 channels of chip 1              */
/*      ADS_READ 2 3    → channel 3 of chip 2                    */
/*      ADS_READ ALL    → all 8 channels (both chips)            */
static void _cmd_ads_read(char *args)
{
    if (!args || *args == '\0') {
        CMD_Send("ERR:Usage: ADS_READ <1|2|ALL> [ch 1-4]");
        return;
    }

    char *cur    = args;
    char *s_chip = _next_token(&cur);
    char *s_ch   = _next_token(&cur);   /* optional */

    /* Uppercase chip arg */
    for (char *p = s_chip; *p; p++) *p = (char)toupper((unsigned char)*p);

    if (strcmp(s_chip, "ALL") == 0)
    {
        /* Read both chips */
        ADS131_Frame_t f1, f2;
        uint8_t ok1 = ADS131A04_ReadFrame(ADS131_CHIP1, &f1);
        uint8_t ok2 = ADS131A04_ReadFrame(ADS131_CHIP2, &f2);
        if (!ok1 || !ok2) {
            CMD_Send("ERR:ADS_READ ALL timeout (ok1=%d ok2=%d)", ok1, ok2);
            return;
        }
        /* Send as integer ×10000 to avoid float printf */
        CMD_Send("DATA:C1CH1=%ld,C1CH2=%ld,C1CH3=%ld,C1CH4=%ld,"
                 "C2CH1=%ld,C2CH2=%ld,C2CH3=%ld,C2CH4=%ld",
                 (long)(f1.voltage[0]*10000), (long)(f1.voltage[1]*10000),
                 (long)(f1.voltage[2]*10000), (long)(f1.voltage[3]*10000),
                 (long)(f2.voltage[0]*10000), (long)(f2.voltage[1]*10000),
                 (long)(f2.voltage[2]*10000), (long)(f2.voltage[3]*10000));
    }
    else
    {
        int ok_chip;
        uint32_t chip = _parse_uint(s_chip, &ok_chip);
        if (!ok_chip || (chip != 1 && chip != 2)) {
            CMD_Send("ERR:chip must be 1, 2, or ALL");
            return;
        }

        ADS131_Frame_t frame;
        if (!ADS131A04_ReadFrame((uint8_t)chip, &frame)) {
            CMD_Send("ERR:ADS_READ chip%d DRDY timeout", (int)chip);
            return;
        }

        if (s_ch)
        {
            /* Single channel requested */
            int ok_ch;
            uint32_t ch = _parse_uint(s_ch, &ok_ch);
            if (!ok_ch || ch < 1 || ch > 4) {
                CMD_Send("ERR:ch must be 1-4");
                return;
            }
            long v = (long)(frame.voltage[ch-1] * 10000);
            CMD_Send("DATA:C%dCH%d=%ld", (int)chip, (int)ch, v);
        }
        else
        {
            /* All 4 channels of this chip */
            CMD_Send("DATA:C%dCH1=%ld,C%dCH2=%ld,C%dCH3=%ld,C%dCH4=%ld",
                     (int)chip, (long)(frame.voltage[0]*10000),
                     (int)chip, (long)(frame.voltage[1]*10000),
                     (int)chip, (long)(frame.voltage[2]*10000),
                     (int)chip, (long)(frame.voltage[3]*10000));
        }
    }
}

/* ── ADS_STATUS <chip> ───────────────────────────────────────── */
/* Read key registers and report chip health                      */
static void _cmd_ads_status(char *args)
{
    if (!args || *args == '\0') {
        CMD_Send("ERR:Usage: ADS_STATUS <1|2>");
        return;
    }
    int ok;
    uint32_t chip = _parse_uint(_trim(args), &ok);
    if (!ok || (chip != 1 && chip != 2)) {
        CMD_Send("ERR:chip must be 1 or 2");
        return;
    }
    uint8_t id    = ADS131A04_ReadReg((uint8_t)chip, ADS131_REG_ID_MSB);
    uint8_t stat1 = ADS131A04_ReadReg((uint8_t)chip, ADS131_REG_STAT_1);
    uint8_t clk1  = ADS131A04_ReadReg((uint8_t)chip, ADS131_REG_CLK1);
    uint8_t clk2  = ADS131A04_ReadReg((uint8_t)chip, ADS131_REG_CLK2);
    uint8_t ena   = ADS131A04_ReadReg((uint8_t)chip, ADS131_REG_ADC_ENA);
    CMD_Send("OK:ADS%d ID=0x%02X STAT=0x%02X CLK1=0x%02X CLK2=0x%02X ENA=0x%02X",
             (int)chip, id, stat1, clk1, clk2, ena);
}

/* ── ADS_CONFIG <chip> <osr> ─────────────────────────────────── */
/* Change OSR on the fly. osr values match ADS131_OSR_t enum.    */
/* e.g. ADS_CONFIG 1 32    → OSR=32 → 62.5kSPS at fMOD=2MHz     */
/*      ADS_CONFIG 1 400   → OSR=400 → 5kSPS                     */
static void _cmd_ads_config(char *args)
{
    char *cur    = args;
    char *s_chip = _next_token(&cur);
    char *s_osr  = _next_token(&cur);
    if (!s_chip || !s_osr) {
        CMD_Send("ERR:Usage: ADS_CONFIG <chip 1|2> <osr 32|64|128|256|400|512|1024|2048|4096>");
        return;
    }
    int ok1, ok2;
    uint32_t chip    = _parse_uint(s_chip, &ok1);
    uint32_t osr_val = _parse_uint(s_osr,  &ok2);
    if (!ok1 || !ok2 || (chip != 1 && chip != 2)) {
        CMD_Send("ERR:Bad args");
        return;
    }

    /* Map OSR integer value to register enum */
    ADS131_OSR_t osr;
    switch (osr_val) {
        case 32:   osr = ADS131_OSR_32;   break;
        case 64:   osr = ADS131_OSR_64;   break;
        case 128:  osr = ADS131_OSR_128;  break;
        case 256:  osr = ADS131_OSR_256;  break;
        case 400:  osr = ADS131_OSR_400;  break;
        case 512:  osr = ADS131_OSR_512;  break;
        case 1024: osr = ADS131_OSR_1024; break;
        case 2048: osr = ADS131_OSR_2048; break;
        case 4096: osr = ADS131_OSR_4096; break;
        default:
            CMD_Send("ERR:Invalid OSR. Valid: 32,64,128,256,400,512,1024,2048,4096");
            return;
    }
    ADS131A04_SetOSR((uint8_t)chip, osr);
    CMD_Send("OK:ADS%d OSR=%d", (int)chip, (int)osr_val);
}

/* ── ADS_STREAM <chip> <n> ───────────────────────────────────── */
/* Stream n frames from one chip (0 = indefinite)                */
static void _cmd_ads_stream(char *args)
{
    if (_ads_stream_active) {
        CMD_Send("ERR:ADS stream active, send ADS_STOP first");
        return;
    }
    char *cur    = args;
    char *s_chip = _next_token(&cur);
    char *s_n    = _next_token(&cur);
    if (!s_chip || !s_n) {
        CMD_Send("ERR:Usage: ADS_STREAM <chip 1|2> <n frames (0=indefinite)>");
        return;
    }
    int ok1, ok2;
    uint32_t chip = _parse_uint(s_chip, &ok1);
    uint32_t n    = _parse_uint(s_n,    &ok2);
    if (!ok1 || !ok2 || (chip != 1 && chip != 2)) {
        CMD_Send("ERR:chip must be 1 or 2");
        return;
    }
    _ads_stream_chip   = (uint8_t)chip;
    _ads_stream_total  = n;
    _ads_stream_sent   = 0;
    _ads_stream_active = 1;
    CMD_Send("OK:ADS_STREAM_START chip=%d n=%d", (int)chip, (int)n);
}

/* ── ADS_STOP ────────────────────────────────────────────────── */
static void _cmd_ads_stop(char *args)
{
    (void)args;
    if (!_ads_stream_active) {
        CMD_Send("ERR:No active ADS stream");
        return;
    }
    _ads_stream_active = 0;
    CMD_Send("OK:ADS_STREAM_STOP samples=%d", (int)_ads_stream_sent);
}

/* ── ADS_DMA_STREAM <chip> <n> ───────────────────────────────── */
static void _cmd_ads_dma_stream(char *args)
{
    if (_ads_dma_active) {
        CMD_Send("ERR:DMA stream active, send ADS_DMA_STOP first");
        return;
    }
    char *cur    = args;
    char *s_chip = _next_token(&cur);
    char *s_n    = _next_token(&cur);
    if (!s_chip || !s_n) {
        CMD_Send("ERR:Usage: ADS_DMA_STREAM <chip 1|2> <n (0=indefinite)>");
        return;
    }
    int ok1, ok2;
    uint32_t chip = _parse_uint(s_chip, &ok1);
    uint32_t n    = _parse_uint(s_n,    &ok2);
    if (!ok1 || !ok2 || (chip != 1 && chip != 2)) {
        CMD_Send("ERR:chip must be 1 or 2");
        return;
    }
    _ads_dma_chip   = (uint8_t)chip;
    _ads_dma_total  = n;
    _ads_dma_sent   = 0;
    _ads_dma_active = 1;
    g_ads131_dma_stream_chip    = (uint8_t)chip;
    g_ads131_dma_stream_enabled = 1;   /* allow EXTI to trigger DMA */
    CMD_Send("OK:ADS_DMA_STREAM_START chip=%d n=%d", (int)chip, (int)n);
}

/* ── ADS_DMA_STOP ────────────────────────────────────────────── */
static void _cmd_ads_dma_stop(char *args)
{
    (void)args;
    if (!_ads_dma_active) {
        CMD_Send("ERR:No active DMA stream");
        return;
    }
    _ads_dma_active = 0;
    g_ads131_dma_stream_enabled = 0;   /* stop EXTI from triggering DMA */
    CMD_Send("OK:ADS_DMA_STREAM_STOP frames=%lu", (unsigned long)_ads_dma_sent);
}

/* ── ADS_DBG — read DMA chain debug counters ─────────────────── */
static void _cmd_ads_dbg(char *args)
{
    (void)args;
    /* Read NVIC enable register for DMA1_Stream3 (IRQ 14) */
    /* NVIC->ISER[0] bit 14 = DMA1_Stream3_IRQn            */
    uint32_t nvic_dma = (NVIC->ISER[0] >> 14) & 1;
    /* DMA1 Stream3 status register */
    uint32_t dma_cr  = DMA1_Stream3->CR;
    uint32_t dma_ndtr = DMA1_Stream3->NDTR;
    /* SPI2 state */
    extern SPI_HandleTypeDef hspi2;
    extern DMA_HandleTypeDef hdma_spi2_rx;
    uint32_t spi_state = (uint32_t)hspi2.State;
    uint32_t dma_state = (uint32_t)hdma_spi2_rx.State;

    CMD_Send("OK:ADS_DBG EXTI=%lu DMA_START=%lu DMA_DONE=%lu RING=%lu "
             "NVIC_DMA=%lu CR=0x%08lX NDTR=%lu SPI_ST=%lu DMA_ST=%lu",
             (unsigned long)g_dbg_exti_count,
             (unsigned long)g_dbg_dma_start,
             (unsigned long)g_dbg_dma_complete,
             (unsigned long)g_dbg_ring_written,
             (unsigned long)nvic_dma,
             (unsigned long)dma_cr,
             (unsigned long)dma_ndtr,
             (unsigned long)spi_state,
             (unsigned long)dma_state);
}
/* Offset calibration — inputs must be shorted (AINxP to AINxN)  */
/* Reads ADS_CAL_FRAMES frames, averages per channel, reports     */
/* the offset in integer ×10000 units. Python stores and applies  */
/* the correction in software on every subsequent reading.        */
/* The ADS131A04 has no user-writable offset trim registers —     */
/* correction is applied in the Python layer.                     */
#define ADS_CAL_FRAMES   500
static void _cmd_ads_cal(char *args)
{
    if (!args || *args == '\0') {
        CMD_Send("ERR:Usage: ADS_CAL <1|2>");
        return;
    }
    int ok;
    uint32_t chip = _parse_uint(_trim(args), &ok);
    if (!ok || (chip != 1 && chip != 2)) {
        CMD_Send("ERR:chip must be 1 or 2");
        return;
    }

    /* Accumulate ADS_CAL_FRAMES frames */
    int64_t sum_raw[4] = {0, 0, 0, 0};
    ADS131_Frame_t frame;
    uint32_t count = 0;

    for (uint32_t i = 0; i < ADS_CAL_FRAMES; i++)
    {
        if (!ADS131A04_ReadFrame((uint8_t)chip, &frame))
        {
            CMD_Send("ERR:ADS_CAL DRDY timeout at frame %lu", (unsigned long)i);
            return;
        }
        for (int ch = 0; ch < 4; ch++)
            sum_raw[ch] += frame.raw[ch];
        count++;
    }

    /* Compute mean voltage offset per channel (integer ×10000) */
    /* Python divides by 10000 and stores as float offset in V   */
    long v[4];
    for (int ch = 0; ch < 4; ch++)
    {
        int32_t mean_raw = (int32_t)(sum_raw[ch] / (int64_t)count);
        /* Convert raw 24-bit count to voltage ×10000 */
        v[ch] = (long)(((float)mean_raw / 8388608.0f) * ADS131_VREF * 10000.0f);
    }

    CMD_Send("OK:ADS_CAL chip=%d CH1=%ld,CH2=%ld,CH3=%ld,CH4=%ld "
             "n=%lu",
             (int)chip,
             v[0], v[1], v[2], v[3],
             (unsigned long)count);
}

/* TIA_GAIN <A|B> <range>
 *
 *   TIA_GAIN A 2K       → Amp A: 2kΩ  feedback  (±1.22mA)
 *   TIA_GAIN A 20K      → Amp A: 20kΩ feedback  (±122µA)
 *   TIA_GAIN B 20K      → Amp B: 20kΩ feedback  (±122µA)
 *   TIA_GAIN B 200K     → Amp B: 200kΩ feedback (±12.2µA)
 *   TIA_GAIN B 2M       → Amp B: 2MΩ  feedback  (±1.22µA)
 *   TIA_GAIN B OFF      → Amp B: all switches open
 *
 * Response on success:
 *   OK:TIA_A=2K,Rf=2000,TIA_B=20K,Rf=20000
 *
 * Response on error:
 *   ERR:Usage: TIA_GAIN <A|B> <2K|20K|200K|2M|OFF>
 *   ERR:Invalid Amp A range '50K' (valid: 2K 20K)
 *   ERR:Invalid Amp B range '1M'  (valid: 20K 200K 2M OFF)
 */
static void _cmd_tia_gain(char *args)
{
    char *cur   = args;
    char *s_amp = _next_token(&cur);
    char *s_rng = _next_token(&cur);

    if (!s_amp || !s_rng) {
        CMD_Send("ERR:Usage: TIA_GAIN <A|B> <2K|20K|200K|2M|OFF>");
        return;
    }

    /* Uppercase both tokens */
    for (char *p = s_amp; *p; p++) *p = (char)toupper((unsigned char)*p);
    for (char *p = s_rng; *p; p++) *p = (char)toupper((unsigned char)*p);

    if (strcmp(s_amp, "A") == 0)
    {
        TIA_GainA_t g;
        if      (strcmp(s_rng, "2K")  == 0) g = TIA_A_2K;
        else if (strcmp(s_rng, "20K") == 0) g = TIA_A_20K;
        else {
            CMD_Send("ERR:Invalid Amp A range '%s' (valid: 2K 20K)", s_rng);
            return;
        }
        if (TIA_SetGainA(g) != 0) {
            CMD_Send("ERR:TIA_SetGainA failed");
            return;
        }
    }
    else if (strcmp(s_amp, "B") == 0)
    {
        TIA_GainB_t g;
        if      (strcmp(s_rng, "20K")  == 0) g = TIA_B_20K;
        else if (strcmp(s_rng, "200K") == 0) g = TIA_B_200K;
        else if (strcmp(s_rng, "2M")   == 0) g = TIA_B_2M;
        else if (strcmp(s_rng, "OFF")  == 0) g = TIA_B_OFF;
        else {
            CMD_Send("ERR:Invalid Amp B range '%s' (valid: 20K 200K 2M OFF)", s_rng);
            return;
        }
        if (TIA_SetGainB(g) != 0) {
            CMD_Send("ERR:TIA_SetGainB failed");
            return;
        }
    }
    else
    {
        CMD_Send("ERR:Amp must be A or B");
        return;
    }

    /* Echo full state after change */
    TIA_State_t st = TIA_GetState();
    const char *a_str = (st.amp_a == TIA_A_2K)  ? "2K"  : "20K";
    const char *b_str = (st.amp_b == TIA_B_20K)  ? "20K"  :
                        (st.amp_b == TIA_B_200K) ? "200K" :
                        (st.amp_b == TIA_B_2M)   ? "2M"   : "OFF";
    CMD_Send("OK:TIA_A=%s,Rf=%lu,TIA_B=%s,Rf=%lu",
             a_str, (unsigned long)TIA_GetRfA(),
             b_str, (unsigned long)TIA_GetRfB());
}

/* ================================================================
 * Dispatch table — unified, all handlers take char* args
 * (NULL args = no-arg commands, they ignore the pointer)
 * ================================================================*/
typedef struct {
    const char *name;
    void (*handler)(char *args);
} CMD_Entry;

static const CMD_Entry _cmd_table[] = {
    { "IDENTIFY",          _cmd_identify       },
    { "STATUS",            _cmd_status         },
    { "STMDIO_WRITE",      _cmd_dio_write      },
    { "STMDIO_WRITE_PIN",  _cmd_dio_write_pin  },
    { "STMDIO_READ",       _cmd_dio_read       },
    { "STMDIO_READ_PIN",   _cmd_dio_read_pin   },
    { "STMDIO_DIR",        _cmd_dio_dir        },
    { "DAC_SET_ALL",       _cmd_dac_set_all    },
    { "DAC_SET",           _cmd_dac_set        },
    { "DAC_CLEAR",         _cmd_dac_clear      },
    { "STMADC_STREAM",     _cmd_stmadc_stream  },
    { "STMADC_STOP",       _cmd_stmadc_stop    },
    { "STMADC",            _cmd_stmadc         },
	{ "CAPTURE_STEP",      _cmd_capture_step   },
	{ "ADCFAST_CAPTURE",   _cmd_adcfast_capture},
	{ "ADCFAST_DBG",       _cmd_adcfast_dbg    },
    { "ADS_READ",       _cmd_ads_read       },
    { "ADS_STREAM",     _cmd_ads_stream     },
    { "ADS_STOP",       _cmd_ads_stop       },
    { "ADS_CONFIG",     _cmd_ads_config     },
    { "ADS_STATUS",     _cmd_ads_status     },
    { "ADS_CAL",        _cmd_ads_cal        },
    { "ADS_DMA_STREAM", _cmd_ads_dma_stream },
    { "ADS_DMA_STOP",   _cmd_ads_dma_stop   },
    { "ADS_DBG",        _cmd_ads_dbg        },
	{ "TIA_GAIN", 		_cmd_tia_gain },
};
#define CMD_TABLE_SIZE  (sizeof(_cmd_table) / sizeof(_cmd_table[0]))

/* ================================================================
 * CMD_Task — called from while(1) in main.c
 * Handles both: (a) dispatching pending commands, (b) streaming
 * ================================================================*/
void CMD_Task(void)
{
    /* ── (a) Dispatch pending command from ISR ────────────── */
    if (_cmd_pending)
    {
        /* Atomically copy buffer to working copy, release ISR buffer */
        uint32_t len = _rx_len;
        memcpy(_work_buf, (const void *)_rx_buf, len);
        _work_buf[len] = '\0';
        _rx_len        = 0;
        _cmd_pending   = 0;   /* release ISR to accept next line */

        char *cmd_name, *cmd_args;
        _split_cmd(_work_buf, &cmd_name, &cmd_args);

        if (strlen(cmd_name) > 0)
        {
            uint8_t matched = 0;
            for (size_t k = 0; k < CMD_TABLE_SIZE; k++)
            {
                if (strcmp(cmd_name, _cmd_table[k].name) == 0) {
                    _cmd_table[k].handler(cmd_args);
                    matched = 1;
                    break;
                }
            }
            if (!matched)
                CMD_Send("ERR:Unknown command '%s'", cmd_name);
        }
    }

    /* ── (b) STMADC Streaming ───────────────────────────────── */
    if (_stream_active)
    {
        uint32_t now = HAL_GetTick();
        if ((now - _stream_last_ms) >= STMADC_STREAM_INTERVAL_MS)
        {
            _stream_last_ms = now;
            if (_stream_channel == 0) {
                uint32_t v1 = (uint32_t)(ADC_ReadVoltage(1) * 10000.0f);
                uint32_t v2 = (uint32_t)(ADC_ReadVoltage(2) * 10000.0f);
                uint32_t v3 = (uint32_t)(ADC_ReadVoltage(3) * 10000.0f);
                uint32_t v4 = (uint32_t)(ADC_ReadVoltage(4) * 10000.0f);
                CMD_Send("DATA:ch1=%lu,ch2=%lu,ch3=%lu,ch4=%lu",
                         (unsigned long)v1,(unsigned long)v2,
                         (unsigned long)v3,(unsigned long)v4);
            } else {
                uint32_t v = (uint32_t)(ADC_ReadVoltage(_stream_channel) * 10000.0f);
                CMD_Send("DATA:ch%d=%lu", (int)_stream_channel, (unsigned long)v);
            }
            _stream_sent++;
            if (_stream_total > 0 && _stream_sent >= _stream_total) {
                _stream_active = 0;
                CMD_Send("OK:STREAM_DONE samples=%d", (int)_stream_sent);
            }
        }
    }

    /* ── (c) ADS131 ASCII streaming (slow path) ─────────────── */
    if (_ads_stream_active)
    {
        ADS131_Frame_t frame;
        if (ADS131A04_ReadFrame(_ads_stream_chip, &frame))
        {
            CMD_Send("DATA:C%dCH1=%ld,C%dCH2=%ld,C%dCH3=%ld,C%dCH4=%ld",
                     (int)_ads_stream_chip, (long)(frame.voltage[0]*10000),
                     (int)_ads_stream_chip, (long)(frame.voltage[1]*10000),
                     (int)_ads_stream_chip, (long)(frame.voltage[2]*10000),
                     (int)_ads_stream_chip, (long)(frame.voltage[3]*10000));
            _ads_stream_sent++;
            if (_ads_stream_total > 0 && _ads_stream_sent >= _ads_stream_total)
            {
                _ads_stream_active = 0;
                CMD_Send("OK:ADS_STREAM_DONE samples=%d", (int)_ads_stream_sent);
            }
        }
    }

    /* ── (d) ADS131 DMA binary streaming (fast path) ────────── */
    if (_ads_dma_active)
    {
        uint32_t avail = ADS131A04_RingAvailable(_ads_dma_chip);
        if (avail == 0) return;

        uint32_t to_send = (avail > ADS_DMA_PKT_FRAMES) ? ADS_DMA_PKT_FRAMES : avail;

        static uint8_t _dma_pkt[6 + ADS_DMA_PKT_FRAMES * ADS131_DMA_FRAME_BYTES];
        static uint8_t _frame_tmp[ADS131_DMA_FRAME_BYTES];

        _dma_pkt[0] = 'D';
        _dma_pkt[1] = _ads_dma_chip;
        _dma_pkt[2] = (_ads_dma_sent >> 24) & 0xFF;
        _dma_pkt[3] = (_ads_dma_sent >> 16) & 0xFF;
        _dma_pkt[4] = (_ads_dma_sent >>  8) & 0xFF;
        _dma_pkt[5] = (_ads_dma_sent >>  0) & 0xFF;

        uint32_t actual = 0;
        for (uint32_t i = 0; i < to_send; i++)
        {
            if (!ADS131A04_RingPop(_ads_dma_chip, _frame_tmp)) break;
            memcpy(&_dma_pkt[6 + i * ADS131_DMA_FRAME_BYTES],
                   _frame_tmp, ADS131_DMA_FRAME_BYTES);
            actual++;
        }

        if (actual > 0)
        {
            USBD_CDC_HandleTypeDef *hcdc =
                (USBD_CDC_HandleTypeDef *)hUsbDeviceFS.pClassData;
            uint32_t dl = HAL_GetTick() + 5;
            while (hcdc->TxState != 0)
                if (HAL_GetTick() >= dl) return;

            uint16_t pkt_len = (uint16_t)(6 + actual * ADS131_DMA_FRAME_BYTES);
            CDC_Transmit_FS(_dma_pkt, pkt_len);

            _ads_dma_sent += actual;

            if (_ads_dma_total > 0 && _ads_dma_sent >= _ads_dma_total)
            {
                _ads_dma_active = 0;
                g_ads131_dma_stream_enabled = 0;
                CMD_Send("OK:ADS_DMA_STREAM_DONE frames=%lu",
                         (unsigned long)_ads_dma_sent);
            }
        }
    }
}
