---
id: intro
title: Introduction
sidebar_position: 1
---

# AIMLAB Automated Analog IC Test Station

When you tape out an analog IC, characterizing it thoroughly and repeatably across
multiple samples is one of the hardest parts of the job. Manual bench measurements
are slow, inconsistent, and difficult to document. The AIMLAB test station was built
to solve this -- a fully Python-controlled, precision measurement platform that runs
complete characterization sweeps automatically, saves structured data, and produces
publication-ready plots with no manual intervention.

## What the Station Does

The station generates programmable DC bias across 40 independent channels, measures
voltage with 24-bit precision, measures current down to the nanoamp range, and captures
transient waveforms at up to 3.2 MSPS -- all from a single Python session. Two
independent control paths (NI USB-6212 and STM32H743) share the same hardware and
can be selected by jumper, giving flexibility for different measurement needs.

DUTs connect through a ZIF40 adapter chain -- motherboard to daughter board to
package-specific adapter -- making it straightforward to swap between device types
without rewiring the measurement hardware.

## Measurement Capabilities

**MOSFET characterization** is fully implemented and validated. The pipeline extracts
threshold voltage (Vth), transconductance (gm), output characteristics (Id-Vds family
of curves), and body diode forward voltage -- all automatically from a three-test
sequence with no rewiring between tests. Bias points for the output sweep are set
automatically from the Vth extracted in the transfer curve test.

**Op-amp characterization** covers DC gain, offset voltage (Vos), linearity (INL),
output swing, common-mode input range (CMR), DC power supply rejection (PSRR), input
bias current (Ib, Ios), and step response. The step response pipeline captures at
3.2 MSPS using the STM32 internal ADC with DMA, resolving slew rate and overshoot
on a sub-microsecond timescale. All tests run from a single Python class with
consistent save/plot/JSON output structure.

## Hardware Platform

The station is built around five purpose-designed subsystems:

- **40-channel DAC** (5x DAC80508, 16-bit, 0-5V) for programmable bias generation,
  with per-channel RC filters on the last two chips for noise-sensitive measurements
- **8-channel precision ADC** (2x ADS131A04, 24-bit, 476 nV/LSB) with DMA streaming
  up to 62.5 kSPS and live data transfer to the PC over USB
- **Transimpedance amplifier** (OPA3S328, switchable 2k/20k/200k/2M Ohm feedback)
  for current measurement from microamps to milliamps, calibrated against a Keithley 2450
- **STM32H743 MCU** at 480 MHz providing USB CDC control, fast burst ADC capture,
  GPIO, and SPI2 DMA -- all accessible from Python over a simple ASCII command protocol
- **NI USB-6212** providing 16-channel 16-bit analog input at 400 kS/s, two analog
  outputs, 32 digital I/O lines, and hardware counter/trigger via PFI

All subsystems are documented with hardware specs, firmware API, Python API, and
measured performance results.

## Where to Start

- **Setting up the hardware** -- [Hardware Setup](./getting-started/hardware-setup)
- **Installing Python and firmware** -- [Software Setup](./getting-started/software-setup)
- **Understanding the hardware** -- [System Overview](./subsystems/subsystems-overview)
- **Running a MOSFET test** -- [MOSFET Measurements](./measurements/mosfet/mosfet-overview)
- **Running an op-amp test** -- [Op-Amp Measurements](./measurements/opamp/opamp-overview)