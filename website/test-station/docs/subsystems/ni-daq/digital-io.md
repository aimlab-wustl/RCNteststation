---
id: ni-daq-digital-io
title: Digital I/O
sidebar_position: 3
---

# NI DAQ -- Digital I/O

## Overview

The test station exposes eight general-purpose digital I/O lines from the
NI USB-6212: `P0.0–P0.7`. All eight lines pass through an
SN74LVC8T245DGVR voltage translator on the motherboard, allowing the DAQ
to interface with DUT logic at 1.8 V, 3.3 V, or 5 V.

These general-purpose DIO lines are software-timed, so each update requires
USB communication with the DAQ. Testing confirmed a practical toggle rate
of approximately 1 kHz. For faster pulse generation and hardware-timed
signals, use the [PFI and counter interface](./ni-daq-pfi).

## Level Translation -- SN74LVC8T245

DIO0-7 pass through an SN74LVC8T245DGVR bidirectional voltage translator.
The NI DAQ connects to the B side (fixed 5V TTL). The A side faces the DUT bus,
with its voltage set by shunt jumper. Direction is controlled by jumper JP9 on the
DIR pin, which is referenced to VCCA.

| Parameter | Value |
|-----------|-------|
| Channels | 8 bidirectional |
| B side (NI DAQ) | 5V (fixed) |
| A side (DUT bus) | Jumper: 1.8V / 3.3V / 5.0V |

| Jumper | DIR pin | Data flow | Effect |
|--------|---------|-----------|--------|
| JP9 populated | HIGH (`VCCA`) | A → B | NI DAQ reads DUT |
| JP9 removed | LOW (`GND`) | B → A | NI DAQ drives DUT |

## Key Specifications (USB-6212 DIO)

| Parameter | Value |
|-----------|-------|
| DIO lines exposed | 8 (`P0.0–P0.7`) |
| Logic level | 5V |
| Output current | 16 mA max per pin |
| Input low threshold (VIL) | 0.8V max |
| Input high threshold (VIH) | 2.2V min |
| Input protection | ±20 V on up to eight pins |
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
