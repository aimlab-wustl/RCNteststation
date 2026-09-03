---
id: stm32-digital-io
title: Digital I/O
sidebar_position: 1
---

# STM32 -- Digital I/O

## Overview

The STM32H743 exposes 14 digital I/O lines from GPIOD. Each line includes
a 22 Ω series resistor to limit transient current and reduce signal ringing.
DIO0–7 pass through an SN74LVC8T245 voltage translator, allowing the STM32
to communicate with DUT logic at 1.8 V, 3.3 V, or 5 V. These eight lines
share one hardware-selected direction. 
DIO8–9 and DIO12–15 connect directly to the DUT interface at 3.3 V and
can be configured individually as inputs or outputs. DIO10–11 are not
exposed through this interface.

## Pin Mapping

| DIO lines | STM32 pins | Count | Interface |
|-----------|------------|-------|-----------|
| DIO0–7 | PD0–PD7 | 8 | Level-translated; bank direction selected by jumper |
| DIO8–9 | PD8–PD9 | 2 | Direct 3.3 V; individually configurable direction |
| DIO12–15 | PD12–PD15 | 4 | Direct 3.3 V; individually configurable direction |

## Level Translation — SN74LVC8T245

DIO0–7 pass through an SN74LVC8T245 voltage translator. The STM32 connects
to side B at 3.3 V, while side A faces the DUT bus and uses the voltage
selected by the shunt jumper. All eight lines share one direction setting.

| Parameter | Value |
|-----------|-------|
| B side | STM32, 3.3 V |
| A side | DUT bus, selectable 1.8 V / 3.3 V / 5 V |
| Direction control | One jumper for the complete 8-bit bank |

| Jumper | DIR | Data flow | Effect |
|--------|-----|-----------|--------|
| Populated | HIGH | A → B | STM32 reads DUT |
| Removed | LOW | B → A | STM32 drives DUT |

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
// PD0-PD7: bank direction selected by hardware jumper
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

dio = STMDIO()                        # connects using the configured COM port

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