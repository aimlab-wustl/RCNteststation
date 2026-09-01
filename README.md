# RCN Test Station

RCN Test Station is a modular hardware, firmware, software, and documentation project for automated analog IC characterization. The platform is designed to support programmable bias generation, synchronized measurement, Python-based experiment control, and future AI-assisted closed-loop testing.

## Overview

Analog and mixed-signal IC testing often requires repeated measurements across different bias conditions, input signals, and operating points. This project aims to make that process more programmable, repeatable, and scalable by combining custom PCB hardware, embedded firmware, Python control software, and a documentation website.

The long-term goal is to develop a chip-in-the-loop test platform where measurement results can guide future test conditions automatically.

## Repository Structure

```text
RCNteststation/
├── firmware/              STM32 firmware and embedded control code
├── python/                Python scripts for hardware control, automation, and data analysis
├── website/test-station/  Docusaurus documentation website
├── .github/workflows/     GitHub Actions deployment workflow
├── .gitignore
└── README.md
```

## Main Components

### Hardware

The hardware platform is designed to support automated analog IC measurements, including:

- Programmable DAC-based bias generation
- ADC-based voltage and signal measurement
- NI-DAQ and STM32 control interfaces
- Precision voltage reference and power regulation
- ZIF socket or device-under-test interface
- PCB-level routing, grounding, and noise-aware design

### Firmware

The firmware folder contains embedded control code for the STM32-based portion of the test station. This may include communication, SPI control, ADC/DAC coordination, timing, and hardware bring-up routines.

### Python Software

The Python folder contains scripts for controlling the test station and running experiments. Functions include:

- DAC voltage setting
- ADC data acquisition
- NI-DAQ control
- STM32 communication
- Calibration routines
- Automated test sequences
- Data logging and analysis

### Documentation Website

The documentation website is built with Docusaurus and located in:

```text
website/test-station/
```

The website documents the system architecture, hardware design, software control, and automation roadmap.

## Project Status

This project is under active development. Hardware, firmware, software, and documentation will be updated as the test station evolves.
