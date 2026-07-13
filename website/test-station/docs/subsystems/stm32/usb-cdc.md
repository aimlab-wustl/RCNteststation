---
id: stm32-usb-cdc
title: USB CDC
sidebar_position: 3
---

# STM32 -- USB CDC Interface

## Overview

The STM32H743 enumerates as a USB CDC virtual COM port. All Python control goes
through ASCII command strings sent over this interface, with responses prefixed
`OK:`, `ERR:`, or `DATA:`. For large captures, binary payloads are used instead
of ASCII to avoid the 100x throughput penalty of text formatting.

## USB Configuration

| Parameter | Value |
|-----------|-------|
| VID | 0x0483 (STMicroelectronics) |
| PID | 0x5740 |
| COM port (Windows) | COM4 |
| USB clock | HSI48 (48 MHz) |
| LPM | Disabled (USBD_LPM_ENABLED=0) |
| Firmware version string | AIMLAB_TESTSTATION_V3_r1 |

## Command Protocol

All commands are ASCII strings terminated with `\n`. Responses are terminated with `\r\n`.

| Command | Arguments | Description |
|---------|-----------|-------------|
| `IDENTIFY` | -- | Returns firmware version string |
| `STATUS` | -- | Returns PA1-PA4 voltages + stream state |
| `STMDIO_WRITE` | hex mask | Write PD0-PD7 bitmask |
| `STMDIO_WRITE_PIN` | pin, 0/1 | Write one DIO pin |
| `STMDIO_READ` | -- | Read all DIO pins |
| `STMDIO_READ_PIN` | pin | Read one DIO pin |
| `STMDIO_DIR` | pin, IN/OUT | Set pin direction |
| `STMADC_READ` | channel | Read one PA1-PA4 channel |
| `STMADC_READ_ALL` | -- | Read all 4 channels |
| `STMADC_STREAM` | channel, n | Stream n samples (0=indefinite) |
| `STMADC_STOP` | -- | Stop active stream |
| `ADCFAST_CAPTURE` | n, prescaler, period | Fast DMA burst capture on PA1 |
| `ADS_READ` | chip, ch | Read one ADS131A04 channel |
| `ADS_READ ALL` | -- | Read all 8 ADS131A04 channels |
| `ADS_STREAM` | chip, n | Stream ADS131A04 frames (ASCII) |
| `ADS_DMA_STREAM` | chip, n | Stream ADS131A04 frames (binary) |
| `ADS_DMA_STOP` | -- | Stop DMA stream |
| `ADS_CONFIG` | chip, osr | Set ADS131A04 OSR |
| `ADS_CAL` | chip | Run ADS131A04 offset calibration |
| `ADS_STATUS` | chip | Read ADS131A04 registers |
| `DAC_SET` | chip, ch, voltage | Set one DAC80508 channel |
| `DAC_SET_ALL` | voltage | Set all 40 DAC channels |
| `DAC_CLEAR` | -- | Zero all DAC channels |
| `TIA_GAIN` | amp, range | Set TIA feedback resistor |

## Binary Transfer Mode

For large captures, the firmware sends a binary payload instead of ASCII:

```
host  -> ADCFAST_CAPTURE 1000 0 23
board -> BINARY:2000
         <2000 bytes of raw uint16 data, little-endian>
         OK:ADCFAST_DONE n=1000
```

This reduces transfer time from ~10s (ASCII) to ~100ms (binary) for 1000 samples.

## Transport Layer (`cdc_serial.py`)

The `cdc_serial.py` module is a thin pyserial wrapper used by all STM32 Python drivers.
It is not called directly -- `stm_dio.py`, `stm_adc.py`, `stm_adc_fast.py`, `ads131a04.py`,
and `tia.py` all use it internally through a shared singleton port.

```python
from hardware.cdc_serial import open_port, send_command, ping

port = open_port()                    # open COM4, safe to call multiple times
resp = send_command("IDENTIFY")       # -> "OK:AIMLAB_TESTSTATION_V3_r1"
alive = ping()                        # -> True if firmware responds correctly
```

## Safe Hotplug Sequence

Hotplugging USB while the board is powered may forward-bias ESD diodes onto
3.3V IO pins, causing SCR latch-up. Always follow this order:

**Power on:** plug USB first, then enable bench supply.
**Power off:** disable bench supply first, then unplug USB.