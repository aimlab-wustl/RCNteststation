---
id: ni-daq-analog-input
title: Analog Input
sidebar_position: 1
---

# NI DAQ -- Analog Input

## Overview

The USB-6212 provides 16 analog input channels (AI0-AI15), 16-bit, up to 400 kS/s.
AI0-AI3 are buffered on the motherboard with a unity-gain OPA4388IDR before reaching
the DAQ connector. AI4-AI15 connect directly to the edge connector without buffering.
Channels can be configured as 16 single-ended or 8 differential in software.

## Key Specifications (USB-6212 AI)

| Parameter | Value |
|-----------|-------|
| Channels | 16 single-ended or 8 differential |
| Resolution | 16-bit |
| Max sample rate | 400 kS/s (single channel, aggregate) |
| Input ranges | +/-0.2V, +/-1V, +/-5V, +/-10V |
| CMRR (DC-60Hz) | 100 dB |
| Input impedance (on) | >10 GOhm in parallel with 100 pF |
| Noise (10V range) | 295 uVrms |
| Absolute accuracy (10V range) | 2,710 uV full scale |
| Absolute accuracy (0.2V range) | 89 uV full scale |
| Small signal bandwidth | 1.5 MHz |
| Overvoltage protection | +/-30V (device on) |

## Signal Conditioning -- OPA4388 Input Buffer

AI0-AI3 pass through a unity-gain OPA4388IDR buffer on the motherboard. The OPA4388
is a zero-drift precision op-amp specifically suited for ADC buffering -- its zero-drift
architecture eliminates 1/f noise, meaning noise performance stays flat down to DC,
which is important for low-frequency and DC characterization measurements.

| Parameter | OPA4388 Value |
|-----------|--------------|
| Offset voltage | +/-0.25 uV typ, +/-8 uV max (quad) |
| Offset drift | +/-0.005 uV/degC |
| Noise density | 7 nV/sqrtHz @ 1kHz (no 1/f noise) |
| Low freq noise | 0.14 uVpp (0.1-10Hz) |
| CMRR | 140 dB |
| GBW | 10 MHz |
| Settling time | 2 us to 0.01% |

## Python API (`ai.py`)

```python
from hardware import read_single, read_buffered, read_continuous

# Single scan -- one sample per channel
v = read_single(0)                      # ai0 -> float volts
v0, v1, v2 = read_single([0, 1, 2])    # list of channels -> list of floats
all_ch = read_single()                  # all channels from config -> list

# Finite buffered acquisition
volts, times = read_buffered(
    channel=0,
    rate=400_000,        # Hz, max 400 kS/s single channel
    num_samples=4000,
)
# volts: numpy array shape (num_samples,)
# times: numpy array of timestamps in seconds from 0

# Continuous live plot with optional CSV
volts, times = read_continuous(
    channel=0,
    rate=400_000,
    duration=10.0,       # seconds, or None to run indefinitely
    window_sec=0.5,      # rolling window width on live plot
    csv_filename='capture.csv'
)
```

### Configuration (`config.py`)

```python
AI_CHANNELS        = list(range(8))     # ai0-ai7
AI_TERMINAL_CONFIG = "SingleEnded"      # "SingleEnded" | "Differential" | "Pseudodiff"
AI_VOLTAGE_RANGE   = (-10.0, 10.0)     # (min_V, max_V)
AI_DEFAULT_RATE    = 400_000            # Hz
AI_DEFAULT_SAMPLES = 4_000
```

## Measured Performance

Single-channel acquisition confirmed at **400 kS/s** with live streaming and CSV
recording. `read_continuous()` uses a hardware-clocked callback -- no samples are
dropped between chunks at full rate.

*Noise floor and accuracy plots at each input range -- to be added*