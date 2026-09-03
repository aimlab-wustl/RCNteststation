---
id: power
title: Power System
sidebar_position: 1
---

# Power System

## Overview

The station runs from a single **9V DC input** (VU rail, from Rigol DP831 or wall adapter).
Three regulators generate all on-board rails. The 5 V and 3.3 V rails each have separate digital and analog supply nets, with ferrite beads used to attenuate high-frequency noise coupling. Each rail has an LED indicator
and an enable jumper (JP1, JP2, JP5) for independent control.

## Schematic

![Power System Schematic](../../../static/img/Powerschematic.png)

## Rail Architecture

```
9V Input (VU)
  |-- LM1086 (U1, adj) --> DVDD_5V --[JP3, ferrite L3]--> AVDD_5V
  |-- LM1086 (U2, adj) --> DVDD_3V --[JP19, ferrite L2]--> AVDD_3V
  |-- TPS7A2018 (U12)  --> DVDD_1V8  (powered from DVDD_3V)
  `-- ADR4525CRZ       --> 2.5V REF  (analog reference only)
```

## Key Specifications

| Parameter | LM1086 5V (U1) | LM1086 3.3V (U2) | TPS7A2018 1.8V (U12) | ADR4525CRZ 2.5V REF (U18) |
|-----------|---------------|-----------------|---------------------|---------------------|
| Input | 9V (VU) | 9V (VU) | DVDD_3V | AVDD_3V |
| Output | DVDD_5V | DVDD_3V | DVDD_1V8 (fixed) | 2.500V (fixed) |
| Output current | 1.5 A max | 1.5 A max | 300 mA max | -- |
| Dropout voltage | 1.5V at 1.5A | 1.5V at 1.5A | -- | -- |
| Ripple rejection | 75 dB typ | 75 dB typ | Ultra-low noise | Ultra-low noise |
| Set by | R1=500 Ohm, R2=2K pot | R3=500 Ohm, R4=2K pot | Fixed | Fixed |
| Initial accuracy | Trimmed to 5.00 V | Trimmed to 3.30 V | -- | ±0.02% (±0.5 mV) |
| Output formula | Vout = 1.25 x (1 + R2/R1) | Vout = 1.25 x (1 + R4/R3) | -- | -- |

Trim R2 and R4 to hit exactly 5.00V and 3.30V on first use.
See [Hardware Setup](../../getting-started/hardware-setup#ldo-voltage-adjustment) for the trimming procedure.
The 2.5V reference feeds the DAC80508 REF pin (when the external reference jumper is populated) and the TIA reference voltage.

## Rail Summary

| Rail | Net name | Source | Powers |
|------|----------|--------|--------|
| 5 V digital | `DVDD_5V` | LM1086 U1 | DAC digital and NI DAQ interface |
| 5 V analog | `AVDD_5V` | `DVDD_5V` through ferrite bead L3 | DAC/TIAs/buffers/ADC analog supplies |
| 3.3 V digital | `DVDD_3V` | LM1086 U2 | STM32 digital, ADC digital, and level translators |
| 3.3 V analog | `AVDD_3V` | `DVDD_3V` through ferrite bead L2 | STM32 analog supply and ADR4525 reference supply|
| 1.8 V digital | `DVDD_1V8` | TPS7A2018 U12 | Low-voltage digital interfaces |
| 2.5 V reference | `REF` | ADR4525CRZ U18 | Reference for DACs and TIA |
