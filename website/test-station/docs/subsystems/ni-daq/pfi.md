---
id: ni-daq-pfi
title: PFI (Timing & Trigger)
sidebar_position: 4
---

# NI DAQ -- PFI and Counters

## Overview

PFI0-PFI15 are programmable function interface lines that can carry timing signals,
triggers, or serve as high-speed digital I/O. The USB-6212 has two 32-bit hardware
counters (ctr0, ctr1) with an 80 MHz base clock, capable of generating precise pulse
trains, counting edges, and measuring frequency -- all without software timing overhead.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| PFI channels | PFI0-PFI15 |
| Counters | 2x 32-bit (ctr0, ctr1) |
| Counter base clock | 80 MHz internal |
| Base clock accuracy | 50 ppm |
| Counter functions | Pulse generation, edge count, frequency, period, two-edge separation |
| Default counter output | ctr0 -> PFI12, ctr1 -> PFI13 |
| PFI input protection | +/-10V |
| Debounce filter | 125 ns, 6.4 us, 2.56 ms (selectable per input) |

## Python API (`pfi.py`)

```python
from hardware import generate_pulse, stop_pulse, count_edges, measure_frequency, arm_ai_trigger

# Generate hardware pulse train -- no CPU involvement once started
task = generate_pulse(
    frequency=10_000,        # Hz
    duty_cycle=0.5,          # 0.0-1.0
    counter='ctr0',
    output_pfi_line=2,       # reroute output to PFI2 (default PFI12)
)
time.sleep(1.0)
stop_pulse(task)

# Count rising edges on PFI0 over 1 second
n = count_edges(duration=1.0, pfi_line=0, edge='rising', counter='ctr1')
print(f"Count: {n}  (~{n:.0f} Hz)")

# Measure signal frequency on PFI0
freq = measure_frequency(pfi_line=0, meas_time=0.1, counter='ctr1')
print(f"Frequency: {freq:.2f} Hz")

# Arm an AI task to start on PFI0 rising edge
import nidaqmx
from nidaqmx.constants import AcquisitionType
with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    task.timing.cfg_samp_clk_timing(
        rate=100_000, sample_mode=AcquisitionType.FINITE, samps_per_chan=1000
    )
    arm_ai_trigger(task, pfi_line=0, edge='rising')
    task.start()
    data = task.read(number_of_samples_per_channel=1000)
```

### Common Use Cases in AIMLAB

- **Synchronized capture** -- trigger AI acquisition from an external event on PFI0
- **Stimulus + capture** -- generate a step on AO0, trigger ADC capture via PFI
- **Frequency measurement** -- count edges from an oscillator or clock output
- **Clock generation** -- provide a precise reference clock to a DUT via PFI output

## Measured Performance

Hardware counter pulse output confirmed up to **10 MHz** on PFI pins.

*PFI trigger jitter, counter accuracy measurements -- to be added*