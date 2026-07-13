---
id: stm32-digital-io
title: Digital I/O
sidebar_position: 1
---

# STM32 -- Digital I/O

## Overview

The STM32H743 provides 18 GPIO lines across GPIOD. All output pins have a 22 Ohm
series resistor before the connector to limit transient currents. The MCU runs at 3.3V.
DIO0-7 (PD0-7) pass through an SN74LVC8T245DGVR voltage translator identical to the
NI DAQ path, allowing the STM32 to interface with DUT logic at 1.8V, 3.3V, or 5V.
DIO8-9 and DIO12-15 connect directly at 3.3V.

## Pin Mapping

| Label | STM32 Pin | Type | Notes |
|-------|-----------|------|-------|
| DIO0 | PD0 | Bidirectional | Translated (SN74LVC8T245), direction by jumper |
| DIO1 | PD1 | Bidirectional | Translated, direction by jumper |
| DIO2 | PD2 | Bidirectional | Translated, direction by jumper |
| DIO3 | PD3 | Bidirectional | Translated, direction by jumper |
| DIO4 | PD4 | Bidirectional | Translated, direction by jumper |
| DIO5 | PD5 | Bidirectional | Translated, direction by jumper |
| DIO6 | PD6 | Bidirectional | Translated, direction by jumper |
| DIO7 | PD7 | Bidirectional | Translated, direction by jumper |
| DIO8 | PD8 | Bidirectional | Direct 3.3V, switchable direction |
| DIO9 | PD9 | Bidirectional | Direct 3.3V, switchable direction |
| DIO12 | PD12 | Bidirectional | Direct 3.3V, switchable direction |
| DIO13 | PD13 | Bidirectional | Direct 3.3V, switchable direction |
| DIO14 | PD14 | Bidirectional | Direct 3.3V, switchable direction |
| DIO15 | PD15 | Bidirectional | Direct 3.3V, switchable direction |

## Level Translation -- SN74LVC8T245

DIO0-7 pass through an SN74LVC8T245DGVR translator. The STM32 connects to the A side
at 3.3V. The B side faces the DUT bus, with voltage set by shunt jumper. Direction of the
entire 8-bit bank is controlled by a shunt jumper on the DIR pin --
all 8 lines switch direction together.

| Parameter | Value |
|-----------|-------|
| A side (STM32) | 3.3V |
| B side (DUT bus) | Jumper: 1.8V / 3.3V / 5.0V |

| Jumper | State | DIR | Data flow | Effect |
|--------|-------|-----|-----------|--------|
| JP populated | VCCA | HIGH | A -> B | STM32 drives DUT |
| JP removed | GND | LOW | B -> A | STM32 reads DUT |

## Speed Specifications

| Mode | Speed | Notes |
|------|-------|-------|
| Software bit-bang (HAL_GPIO_WritePin in loop) | ~20 MHz max | Limited by AXI/AHB bus bridge latency on H743 |
| Timer-driven output (PWM, one-pulse) | 50 MHz and above | Hardware-clocked, no CPU involvement |
| Firmware DIO write via USB CDC command | ~1 kHz | USB round-trip limited |
| SN74LVC8T245 propagation delay | under 10 ns | At 3.3V, well within any application need |

The STM32H743 GPIO speed setting should be set to `GPIO_SPEED_FREQ_VERY_HIGH` for signals
above a few MHz. The 22 Ohm series resistors limit peak drive current and reduce ringing
but do not significantly affect speed at typical load capacitances on the board.

## Firmware

Driver files: `dio.c`, `dio.h`

```c
// PD0-PD7: write only
void    DIO_Write(uint8_t pin, uint8_t state);
uint8_t DIO_Read(uint8_t pin);

// PD8-PD9: switchable direction
void    DIO_SetDirection(uint8_t pin, DIO_Direction dir);   // DIO_INPUT or DIO_OUTPUT
void    DIO_Write89(uint8_t pin, uint8_t state);
uint8_t DIO_Read89(uint8_t pin);

// PD12-PD15: switchable direction
void    DIO_SetDirection1215(uint8_t pin, DIO_Direction dir);
void    DIO_WritePWM(uint8_t pin, uint8_t state);
uint8_t DIO_ReadPWM(uint8_t pin);
```

## Python API (`stm_dio.py`)

```python
from hardware.stm_dio import STMDIO

dio = STMDIO()                        # connects on COM4

# Write a single pin (0=LOW, 1=HIGH)
dio.write(3, 1)                       # PD3 high
dio.write(12, 0)                      # PD12 low

# Write all 8 lower pins at once (bitmask, bit N = PD-N)
dio.write_mask(0b00001111)            # PD0-PD3 high, PD4-PD7 low
dio.write_mask(0x00FF)                # all 8 high

# Read a single pin
state = dio.read(8)                   # read PD8 -> 0 or 1

# Read all pins at once
states = dio.read_all()               # -> {0:0, 1:1, ..., 9:0, 12:0, ...}
mask = dio.read_mask()                # -> int bitmask

# Set direction for bidirectional pins (8, 9, 12-15)
dio.set_direction(8, "IN")
state = dio.read(8)
dio.set_direction(8, "OUT")
dio.write(8, 1)

# Convenience
dio.pulse(0, duration_ms=5.0)        # 5ms pulse on PD0
dio.clear_all()                       # zero PD0-PD7
dio.print_state()                     # print all pin states to console
```

## Measured Performance

*DIO switching speed and timing characterization -- to be added*