---
id: ni-daq
title: NI DAQ
sidebar_position: 2
---

# NI DAQ -- NI USB-6212

## Overview

The NI USB-6212 is a USB multifunction DAQ providing analog input, analog output,
digital I/O, PFI timing, and counter channels. It connects to the motherboard via an
edge connector and serves as one of the two control paths for the test station.
All I/O is software-timed via NI-DAQmx -- the USB-6212 has no onboard processor
and relies on the host PC for sequencing.

## Key Specifications

| Parameter | Value |
|-----------|-------|
| Analog inputs | 16 single-ended or 8 differential |
| AI resolution | 16-bit |
| AI max sample rate | 400 kS/s (single channel) |
| AI input ranges | +/-0.2V, +/-1V, +/-5V, +/-10V |
| AI CMRR (DC-60Hz) | 100 dB |
| AI absolute accuracy (10V range) | 2,710 uV full scale |
| Analog outputs | 2 (AO0, AO1) |
| AO resolution | 16-bit |
| AO max update rate | 250 kS/s per channel |
| AO output range | +/-10V |
| AO output impedance | 0.2 Ohm, +/-2 mA drive |
| Digital I/O | 32 lines (P0.0-15, PFI0-15) |
| DIO logic level | 5V TTL |
| DIO reliable toggle rate | ~1 kHz (software-timed) |
| DIO output current | 16 mA max per pin |
| PFI channels | PFI0-PFI15 |
| Counters | 2x 32-bit (ctr0, ctr1), 80 MHz base clock |
| Interface | USB 2.0 Hi-Speed |
| Driver | NI-DAQmx |

## Sub-sections

- [Analog Input](./ni-daq-analog-input) -- AI0-15, OPA4388 buffer, `ai.py` API
- [Analog Output](./ni-daq-analog-output) -- AO0/AO1, `ao.py` API
- [Digital I/O](./ni-daq-digital-io) -- DIO, level translation, `dio.py` API
- [PFI](./ni-daq-pfi) -- PFI0-15, counters, `pfi.py` API

## Measured Performance

AI confirmed at **400 kS/s** single channel with live streaming and CSV capture.
DIO reliable toggle rate approximately **1 kHz** due to USB software-timing overhead.
Hardware counter output via PFI can generate signals up to **10 MHz**.