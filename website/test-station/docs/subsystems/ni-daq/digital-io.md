---
id: ni-daq-digital-io
title: Digital I/O
sidebar_position: 3
---

# NI DAQ -- Digital I/O

## Overview

The USB-6212 provides up to 32 digital I/O lines at 5V TTL logic. DIO0-7 (P0.0-7)
pass through an SN74LVC8T245DGVR voltage translator on the motherboard before reaching
the DIO bus, allowing the DAQ to interface with DUT logic at 1.8V, 3.3V, or 5V.
DIO8-15 (P0.8-15) connect directly at 5V TTL without translation.

All DIO is software-timed -- each write involves a USB round-trip. Reliable toggle
rate is approximately 1 kHz. For faster digital signaling use the
[PFI counter output](./ni-daq-pfi) instead.

## Level Translation -- SN74LVC8T245

DIO0-7 pass through an SN74LVC8T245DGVR bidirectional voltage translator.
The NI DAQ connects to the B side (fixed 5V TTL). The A side faces the DUT bus,
with its voltage set by shunt jumper. Direction is controlled by jumper JP9 on the
DIR pin, which is referenced to VCCA.

| Parameter | Value |
|-----------|-------|
| Channels | 8 bidirectional |
| B side (NI DAQ) | 5V TTL (fixed) |
| A side (DUT bus) | Jumper: 1.8V / 3.3V / 5.0V |

| Jumper | State | DIR pin | Data flow | Effect |
|--------|-------|---------|-----------|--------|
| JP9 populated | VCCA | HIGH | B -> A | NI DAQ drives DUT |
| JP9 removed | GND | LOW | A -> B | NI DAQ reads DUT |

## Key Specifications (USB-6212 DIO)

| Parameter | Value |
|-----------|-------|
| Total DIO lines | 32 (P0.0-15 + PFI0-15) |
| Logic level | 5V TTL |
| Output current | 16 mA max per pin |
| Input low threshold (VIL) | 0.8V max |
| Input high threshold (VIH) | 2.2V min |
| Input protection | +/-20V |
| Pull-down resistor | 50 kOhm typ |
| Reliable toggle rate | ~1 kHz (software-timed) |

## Python API (`dio.py`)

```python
from hardware import set_line, get_line, set_port, get_port, DIOOutputSession, loopback_line

# Single line -- True = HIGH, False = LOW
set_line(4, True)                    # P0.4 HIGH
set_line(4, False)                   # P0.4 LOW
state = get_line(6)                  # read P0.6 -> bool

# Multiple lines at once
set_port([1, 2, 3, 4], [True, False, False, True])
states = get_port([6, 7])            # -> [bool, bool]

# Hold output lines driven while doing other work
# (prevents DAQmx task close from releasing the line between writes)
with DIOOutputSession([0, 1, 2], initial_values=[False, False, False]) as dio:
    dio.write([True, False, True])   # update all 3 lines
    dio.set_line(0, False)           # update one line
    state = get_line(5)              # read another line while output held

# Loopback test -- wire output_line to input_line externally before running
results = loopback_line(output_line=0, input_line=6)
# -> [True, False, True, False] -- one bool per state tested
```

## Measured Performance

DIO reliable toggle rate confirmed at approximately **1 kHz** under software-timed USB operation. Each `set_line()` call incurs a USB round-trip of roughly 1 ms, setting the practical ceiling for bit-banged signaling. For higher speeds, use the PFI counter output which can generate up to 10 MHz in hardware.

*Setup/hold timing characterization -- to be added**