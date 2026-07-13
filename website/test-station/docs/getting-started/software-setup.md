---
id: software-setup
title: Software Setup
sidebar_position: 2
---

# Software Setup

## 1. Firmware (STM32)

### Required Tools

- **STM32CubeIDE v2.1.1** -- IDE and compiler
- **STM32CubeMX** -- peripheral configuration (standalone)
- **STM32CubeProgrammer** -- for connection diagnostics and manual flash
- **STLINK-V3MINIE** -- SWD debugger

### Get the Firmware

Clone or download the firmware from the repository:

```
https://github.com/kaiyuank/Automated-Analog-IC-Test-Station/tree/main/firmware
```

### Flashing Firmware

1. Open STM32CubeIDE
2. Import the firmware project (`File --> Import --> Existing Projects`)
3. Connect STLINK to the SWD header (see [Hardware Setup](./hardware-setup#swd-programming-port))
4. Power the board
5. Click **Run** (or **Debug**) to build and flash
6. Verify: the USB CDC device enumerates as `COM4` (Windows) after flashing

### Verifying USB CDC Enumeration

- Windows Device Manager: `STMicroelectronics Virtual COM Port (COM4)`
- VID: `0483`, PID: `5740`
- If COM port does not appear, check the D+/D- solder joints on the USB connector

---

## 2. Python Environment

All Python control scripts run in the `test-station` conda environment.
Scripts are located at:

```
https://github.com/kaiyuank/Automated-Analog-IC-Test-Station/tree/main/python
```

### Quick Setup (Recommended)

A setup script is provided in the repository to create the environment and install all dependencies in one step:

```bash
conda env create -f environment.yml
conda activate test-station
```

### Manual Setup

If you prefer to set up manually:

```bash
conda create -n test-station python=3.13
conda activate test-station
pip install -r requirements.txt
```

### Full Package List

```
# DAQ and instrument control
nidaqmx          # NI USB-6212 control
pyvisa           # Keithley 2450 VISA interface
pyserial         # STM32 USB CDC communication

# Numerical and scientific
numpy
scipy
pandas

# Plotting
matplotlib

# Data storage
h5py             # HDF5 for large measurement datasets

# Utilities
tqdm             # Progress bars for long sweeps
```

### Scripts Path Convention

All scripts use `SCRIPT_DIR` so outputs save next to the script regardless of where Python is launched from:

```python
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
```

---

## 3. NI-DAQmx Driver

The NI USB-6212 requires the NI-DAQmx driver installed on the host PC.

1. Download **NI-DAQmx** from [ni.com/downloads](https://www.ni.com/downloads)
2. Run the installer -- select at minimum: `NI-DAQmx`, `NI-MAX`
3. Open **NI MAX** (Measurement & Automation Explorer)
4. Under `Devices and Interfaces`, verify `NI USB-6212 "Dev1"` appears
5. Right-click --> **Self-Test** to confirm hardware communication

---

## 4. NI-VISA (Keithley 2450)

The Keithley 2450 SMU is controlled via VISA over USB.

1. Download **NI-VISA** from [ni.com/downloads](https://www.ni.com/downloads)
2. Install alongside NI-DAQmx
3. In NI MAX, verify the Keithley appears under `Devices and Interfaces --> VISA`
4. VISA address: `USB0::0x05E6::0x2450::04345889::INSTR`

```python
import pyvisa
rm = pyvisa.ResourceManager()
keithley = rm.open_resource('USB0::0x05E6::0x2450::04345889::INSTR')
print(keithley.query('*IDN?'))
```

---

## 5. Verify Everything

Run this quick check to confirm all interfaces are working:

```python
# NI DAQ
import nidaqmx
with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    print("NI DAQ AI0:", task.read())

# STM32 USB CDC
from hardware.cdc_serial import open_port, ping
open_port()
print("STM32 alive:", ping())

# Keithley 2450
import pyvisa
rm = pyvisa.ResourceManager()
k = rm.open_resource('USB0::0x05E6::0x2450::04345889::INSTR')
print("Keithley:", k.query('*IDN?'))
```

---

## 6. config.py

Before running any scripts, check `config.py` in the Python root and verify:

```python
DEVICE       = "Dev1"          # NI DAQ device name -- check NI MAX
STM_COM_PORT = "COM4"          # STM32 CDC port -- check Device Manager
DAC_VERSION  = "DAC80508"      # "LTC2600" | "AD5676R" | "DAC80508"
```