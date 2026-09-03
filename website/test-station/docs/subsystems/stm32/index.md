---
id: stm32
title: STM32
sidebar_position: 3
---

# STM32H743 -- Microcontroller

## Overview

The STM32H743VIT6 is the embedded controller for the test station, running at 480 MHz on a Cortex-M7 core. It drives the DAC daisy chain, reads both ADS131A04 ADC chips via SPI2 DMA, controls TIA gain switching, and communicates with the host PC over USB CDC. It also exposes 14 GPIO lines for DIO and four internal ADC channels capable of burst captures up to 3.2 MSPS for step response and transient measurements.

All GPIO outputs have a 22 Ohm series resistor before the pin to limit transient currents and reduce ringing on the PCB traces.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Part | STM32H743VIT6 |
| Core | Cortex-M7, 480 MHz |
| Flash | 2 MB |
| RAM | 1 MB |
| Supply | 3.3V (LM1086) |
| Crystal | 8 MHz |
| USB | Full-speed (USB FS), USBLC6-2SC6 ESD protection |
| USB VID/PID | 0x0483 / 0x5740 |
| COM port | Assigned by Windows (for example, `COM4`) |
| Programming | SWD via STLINK-V3MINIE |

## Sub-sections

- [Digital I/O](./stm32-digital-io) -- 14 lines on PD0–PD9 and PD12–PD15
- [Internal ADC](./stm32-internal-adc) -- PA1-PA4, fast burst capture up to 3.2 MSPS, `stm_adc.py` / `stm_adc_fast.py`
- [USB CDC](./stm32-usb-cdc) -- Command protocol, VID/PID, safe hotplug sequence

## USB Safe Hotplug Sequence

Hotplugging USB while the board is powered may forward-bias ESD diodes onto the 3.3V IO pins, causing SCR latch-up on the STM32. Always follow this sequence:

**Power on:** Plug in USB first, then enable the bench power supply.  
**Power off:** Disable the bench power supply first, then unplug USB.