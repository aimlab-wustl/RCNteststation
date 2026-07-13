---
id: hardware-setup
title: Hardware Setup
sidebar_position: 1
---

# Hardware Setup

## Power Supply

The station accepts **9V DC input**, either from a Rigol DP831 bench supply or an external adapter.

### LDO Voltage Adjustment

Two LM1086 LDOs generate the 5V and 3.3V rails using an adjustable resistor divider (R1/R2 for 5V, R3/R4 for 3.3V). Each has a 2K potentiometer that must be trimmed on first use.

1. Connect 9V input -- do **not** connect USB or DUT yet
2. Power on the supply
3. Measure DVDD_5V at the test point with a DMM
4. Trim R2 potentiometer until you read **5.00V +/-20mV**
5. Repeat for DVDD_3V with R4: target **3.30V +/-15mV**
6. Verify DVDD_1V8 (TPS7A2018, fixed -- no adjustment needed)
7. Verify the 2.5V reference (ADR4525CRZ): **2.500V +/-5mV**

:::warning USB Latch-Up Risk
Always plug in USB **before** enabling the bench supply. Hotplugging USB while the board is powered may forward-bias ESD diodes onto the STM32 3.3V IO pins and cause SCR latch-up. At least one latch-up event has occurred requiring days unpowered to recover.

**Power on:** plug USB first, then enable bench supply.
**Power off:** disable bench supply first, then unplug USB.
:::

### Power Rails Summary

| Rail | Net name | Regulator | Powers |
|------|----------|-----------|--------|
| 5V digital | DVDD_5V | LM1086 U1 | DAC logic, NI DAQ edge connector |
| 5V analog | AVDD_5V | DVDD_5V + ferrite L3 | DAC analog outputs |
| 3.3V digital | DVDD_3V | LM1086 U2 | STM32, ADC digital, level translators |
| 3.3V analog | AVDD_3V | DVDD_3V + ferrite L2 | ADC analog front end |
| 1.8V | DVDD_1V8 | TPS7A2018 U12 | Low-voltage logic |
| 2.5V REF | -- | ADR4525CRZ | DAC reference, TIA reference |

---

## Jumper Configuration

### Control Path (DAC Daisy Chain)

Selects whether the DAC80508 5-chip daisy chain is driven by the NI USB-6212 or the STM32.

| Jumper | Position | DAC controlled by |
|--------|----------|------------------|
| JP_DAC_SEL | NI | NI USB-6212 (bit-bang DIO, port0/line1-3) |
| JP_DAC_SEL | STM | STM32H743 (PE11 SDI, PE12 SCLK, PE14 CS) |

Only one path should be active at a time.

### DAC Reference Select

A 0 Ohm resistor jumper selects internal or external reference for the DAC80508.
When populated, the REF pin connects to the ADR4525CRZ external 2.5V reference.
When removed, the internal 2.5V reference is used. Both give 0-5V output range (gain=2).

When the 0 Ohm jumper is populated, ensure the firmware and Python driver are
configured to use the external reference -- two voltage sources contending on the
REF pin will pull it to an intermediate voltage and corrupt DAC output accuracy.
On the NI path use `dac_initialize(use_external_ref=True)`. On the STM32 path the
firmware disables the internal reference when external is selected.

### DIO Direction and Voltage (SN74LVC8T245)

Two SN74LVC8T245 translators handle DIO -- one for NI DAQ DIO0-7, one for STM32 DIO0-7.
Each has two jumper controls:

**Direction -- NI DAQ translator (JP9, DIR pin referenced to VCCA):**

| Jumper | DIR pin | Data flow | Effect |
|--------|---------|-----------|--------|
| JP9 populated | HIGH (VCCA) | B to A | NI DAQ drives DUT |
| JP9 removed | LOW (GND) | A to B | NI DAQ reads DUT |

**Direction -- STM32 translator (JP33, DIR pin referenced to VCCA):**

| Jumper | DIR pin | Data flow | Effect |
|--------|---------|-----------|--------|
| JP33 populated | HIGH (VCCA) | B to A | STM32 drives DUT |
| JP33 removed | LOW (GND) | A to B | STM32 reads DUT |

**Voltage -- Side B (DUT-facing):**

| Jumper | DUT-side voltage |
|--------|-----------------|
| JP_VB = 1.8 | 1.8V |
| JP_VB = 3.3 | 3.3V |
| JP_VB = 5.0 | 5.0V |

NI DAQ DIO connects to the B side at 5V TTL. STM32 DIO0-7 connects to the A side at 3.3V.

---

## DUT Connection

Devices under test connect through a three-stage ZIF40 chain:

```
Motherboard (4x ZIF40 female)
  --> Daughter board (4x ZIF40 male + ZIF40 female)
        --> DUT adapter --> Device Under Test
```

1. Select the correct DUT adapter for your package type
2. Insert DUT into the adapter -- verify pin 1 orientation
3. Connect adapter to the ZIF40 female connector on the daughter board
4. Connect daughter board to the motherboard ZIF40 connectors
5. Before applying power, set all DAC outputs to 0V

:::warning
Always ramp bias voltages slowly to the operating point after connecting the DUT.
Never remove a DUT while bias voltages are applied.
:::

---

## SWD Programming Port

The STM32 firmware is loaded via SWD using an STLINK-V3MINIE debugger.

| Pin | Signal |
|-----|--------|
| 1 | DVDD_3V (3.3V target power sense) |
| 2 | SWDIO |
| 3 | SWCLK |
| 4 | SWO |
| 5 | NRST |
| 6 | GND |

Connect the STLINK before powering the board. After flashing, the STM32 enumerates as USB CDC on COM4 (VID 0x0483, PID 0x5740).