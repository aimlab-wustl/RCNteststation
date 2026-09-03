---
id: pcb-overview
title: PCB Overview
sidebar_position: 1
---

# PCB Overview

## Board Summary

| Parameter | Value |
|-----------|-------|
| Current design revision | V3 |
| Architecture | Motherboard and daughterboard |
| DUT interface | Four ZIF40 board-to-board connections |
| EDA tool | Altium Designer |
| Power input | 9 V DC from a bench supply or external adapter |
| Main controllers | NI USB-6212 and STM32H743 |
| Precision outputs | 40-channel, 16-bit DAC subsystem |
| Precision inputs | Eight-channel, 24-bit ADC subsystem |

## System Block Diagram

![System block diagram](/img/blockdiagramnew.png)

The test station supports both NI USB-6212 and STM32 control paths. A
jumper selects which controller drives the DAC daisy chain; the remaining
subsystems retain their dedicated control and acquisition paths. The NI USB-6212
supports analog I/O, general digital I/O, and PFI timing, while the STM32H743
provides USB CDC control, precision ADC acquisition, DAC control, TIA range
selection, and fast transient capture.

The ADS131A04 subsystem provides eight differential channels in total.
The current continuous DMA implementation streams four simultaneous channels
from one ADC at a time.

## V3 Motherboard

### 3D Rendering

![V3 motherboard 3D rendering](/img/3D_PCB.png)

The V3 motherboard integrates the STM32 controller, precision DAC and ADC
subsystems, selectable TIA ranges, power regulation, and interfaces for the
NI USB-6212 and daughterboard.

### PCB Layout

![V3 motherboard PCB layout](/img/pcbtraces.png)

The six-layer motherboard routes precision analog signals, digital control
lines, power rails, and the four daughterboard connections.

## V3 Daughterboard

### 3D Rendering

![V3 daughterboard 3D rendering](/img/pcbdaughter3D.png)

The V3 daughterboard connects the motherboard measurement resources to the
central 40-pin DUT socket. It routes DAC outputs, precision ADC inputs, TIA
connections, power and reference rails, general digital I/O, and PFI timing
signals to the DUT.

### PCB Layout

![V3 daughterboard PCB layout](/img/pcbdaughterlayout.png)

The daughterboard organizes the analog, digital, timing, and power connections
from the motherboard and routes them to the DUT socket.

## Main Interfaces

| Interface | Function |
|-----------|----------|
| Four ZIF40 connectors | Motherboard-to-daughterboard connection |
| NI DAQ edge connector | NI USB-6212 analog, digital, and PFI signals |
| STM32 USB connector | USB CDC communication with the host PC |
| SWD header | STM32 firmware programming and debugging |
| 9 V input | Main board power input |

## Current Revision

All Altium source files and fabrication packages currently included in the
repository correspond to **V3**. Earlier board versions used different DAC
devices and are described in the [DAC documentation](../subsystems/dac), but
their PCB source files are not included in the current release.

See [Design Files](./pcb-files) for the Altium sources and fabrication packages.