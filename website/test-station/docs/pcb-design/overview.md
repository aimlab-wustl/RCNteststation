---
id: pcb-overview
title: PCB Overview
sidebar_position: 1
---

# PCB Overview

## Board Photo

*PCB photo — to be added*

## Board Summary

| Parameter | Value |
|-----------|-------|
| Board version | V3 (AIMLAB_TESTSTATION_V3) |
| Form factor | Motherboard + daughter board |
| DUT interface | 4× ZIF40 connectors |
| EDA tool | Altium Designer |
| Power input | 9V DC (barrel jack or DP831) |

## Block Diagram

*Full system block diagram — to be added*

## Connector Map

| Connector | Function |
|-----------|----------|
| ZIF40 J1–J4 (female) | Motherboard → daughter board |
| Edge connector J5 | NI USB-6212 interface |
| J6 | 9V power input |
| J7 | SWD programming (STM32) |
| J8 | USB FS (STM32 CDC) |

## Board Versions

| Version | DAC Chip | Notes |
|---------|----------|-------|
| V1 | LTC2600 | First prototype |
| V2 | AD5676R | Improved DAC, same layout |
| V3 (current) | DAC80508 | Best linearity, USB fix, TIA added |
