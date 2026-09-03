---
id: ni-daq-analog-output
title: Analog Output
sidebar_position: 2
---

# NI DAQ -- Analog Output

## Overview

The USB-6212 has two internal 16-bit DAC channels (AO0, AO1) with a +/-10V output
range. These are available for general-purpose voltage sourcing -- useful for low-channel-count
biasing, AC stimulus generation, or reference voltages where the 40-channel DAC80508 is not needed.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Channels | 2 (AO0, AO1) |
| Resolution | 16-bit |
| Output range | +/-10V |
| Max update rate | 250 kS/s per channel |
| Output impedance | 0.2 Ohm |
| Output current drive | +/-2 mA |
| Absolute accuracy (10V range) | 3,512 uV full scale |
| Settling time (1 LSB) | 32 us |
| Slew rate | 5 V/us |
| Power-on state | +/-20 mV |
| Overdrive protection | +/-30V |

## Python API (`ao.py`)

```python
from hardware import write_single, write_all, zero_all

# Set one channel
write_single(0, 2.5)             # ao0 = 2.5V
write_single(1, -1.0)            # ao1 = -1.0V

# Set both channels simultaneously
write_all([1.0, 2.5])            # ao0=1.0V, ao1=2.5V

# Safe shutdown -- set both outputs to 0 V
zero_all()
```

### Configuration (`config.py`)

```python
AO_CHANNELS      = [0, 1]
AO_VOLTAGE_RANGE = (0.0, 10.0)   # clamp range for write_single/write_all
```

Values outside `AO_VOLTAGE_RANGE` are clamped with a warning rather than raising an error.