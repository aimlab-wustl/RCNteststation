---
id: software-setup
title: Software Setup
sidebar_position: 2
---

# Software Setup

## 1. Firmware (STM32)

### Required Tools

- **STM32CubeIDE v2.1.1** -- IDE and compiler
- **STM32CubeMX** -- peripheral configuration
- **STM32CubeProgrammer** -- connection diagnostics and manual flash
- **STLINK-V3MINIE** -- SWD debugger

### Get the Firmware

The STM32 firmware is located in the repository:

[firmware/test_station_fw](https://github.com/aimlab-wustl/RCNteststation/tree/main/firmware/test_station_fw)

### Flashing Firmware

1. Open STM32CubeIDE.
2. Import the firmware project: `File --> Import --> Existing Projects`.
3. Connect STLINK to the SWD header. See [Hardware Setup](./hardware-setup#swd-programming-port).
4. Power the board.
5. Click **Run** or **Debug** to build and flash.
6. Verify that the STM32 appears as a USB CDC virtual COM port after flashing.

### Verifying USB CDC Enumeration

1. Open **Windows Device Manager**.
2. Expand **Ports (COM & LPT)**.
3. Find `STMicroelectronics Virtual COM Port`.
4. Note its assigned port number, such as `COM4` or `COM7`.
5. Enter that port number as `STM_COM_PORT` in `config.py`.

The expected USB identifiers are VID `0483` and PID `5740`. If the COM
port does not appear, check the USB cable, driver installation, and the
D+/D− connections on the board.
---

## 2. Python Environment

All Python control scripts run in the `test-station` conda environment.

The Python control scripts are located in the repository:

[python](https://github.com/aimlab-wustl/RCNteststation/tree/main/python)

### Quick Setup

Create the environment and install dependencies:

```bash
conda create -n test-station python=3.13
conda activate test-station
pip install -r requirements.txt
```

### Main Python Packages

```text
# DAQ and instrument control
nidaqmx          # NI USB-6212 control
pyvisa           # Keithley 2450 VISA interface
pyserial         # STM32 USB CDC communication

# Numerical and scientific computing
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

All scripts use `SCRIPT_DIR` so outputs are saved next to the script regardless of where Python is launched from:

```python
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
```

---

## 3. NI-DAQmx Driver

The NI USB-6212 requires the NI-DAQmx driver installed on the host PC.

1. Download **NI-DAQmx** from [NI Downloads](https://www.ni.com/downloads).
2. Run the installer and select at minimum: `NI-DAQmx` and `NI-MAX`.
3. Open **NI MAX**.
4. Under `Devices and Interfaces`, verify that `NI USB-6212 "Dev1"` appears.
5. Right-click the device and select **Self-Test** to confirm hardware communication.

---

## 4. NI-VISA for Keithley 2450

The Keithley 2450 SMU is controlled through VISA over USB.

1. Download **NI-VISA** from [NI Downloads](https://www.ni.com/downloads).
2. Install it alongside NI-DAQmx.
3. In NI MAX, verify that the Keithley appears under `Devices and Interfaces --> VISA`.
4. Use the VISA address:

```text
USB0::0x05E6::0x2450::04345889::INSTR
```

Example Python check:

```python
import pyvisa

rm = pyvisa.ResourceManager()
keithley = rm.open_resource('USB0::0x05E6::0x2450::04345889::INSTR')

print(keithley.query('*IDN?'))
```

---

## 5. Verify Everything

Run this quick check to confirm the main interfaces are working:

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

## 6. `config.py`

Before running any scripts, check `config.py` in the Python root and verify:

```python
DEVICE = "Dev1"              # NI DAQ device name; verify in NI MAX
STM_COM_PORT = "COM4"        # Replace with the port shown in Device Manager
DAC_VERSION = "DAC80508"     # "LTC2600" | "AD5676R" | "DAC80508"
```