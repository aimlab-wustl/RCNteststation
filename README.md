# Automated Analog and Neuromorphic Integrated Circuits Test-Station

Characterizing a fabricated analog or neuromorphic IC often requires several instruments, separate software interfaces, and repeated manual setup for each device. This makes measurements slow to run and difficult to reproduce. The test station brings programmable biasing, precision voltage and current measurement, fast transient capture, and Python control into one modular system so that researchers can reuse the hardware and compare results across devices.

This project is supported in part by a Research Coordination Network (RCN) grant from the National Science Foundation (NSF), grant no. **2332166**.

[System documentation](https://aimlab-wustl.github.io/RCNteststation/) · [Hardware setup](https://aimlab-wustl.github.io/RCNteststation/docs/getting-started/hardware-setup) · [Software setup](https://aimlab-wustl.github.io/RCNteststation/docs/getting-started/software-setup)

## Test station system

| Subsystem | V3 implementation |
| --- | --- |
| Programmable bias | Five DAC80508 devices provide 40 independent 16-bit outputs over 0–5 V. A jumper selects NI USB-6212 or STM32H743 control. |
| Precision voltage acquisition | Two ADS131A04 devices provide eight differential 24-bit inputs. The current DMA implementation streams four channels from one chip at a time, up to 62.5 kSPS per channel. |
| Current measurement | Two OPA3S328 transimpedance circuits provide selectable nominal feedback from 2 kΩ to 2 MΩ, with their outputs measured by the precision ADC. |
| Fast transient capture | The STM32H743 internal ADC captures up to 8,000 samples at up to 3.2 MSPS on PA1 using timer-triggered DMA. |
| DUT connection | A ZIF40 daughterboard and package-specific adapter route bias, measurement, digital I/O, and timing signals to the device under test. |

## Firmware and Python control

STM32 firmware handles USB CDC communication, DAC control, ADS131A04 acquisition, TIA range selection, and transient capture. The NI USB-6212 provides a second control path and bench analog I/O. Python modules in [`python/hardware/`](python/hardware/) expose these functions to measurement scripts, which save data and generate plots for repeatable tests.

The [DAC characterization](https://aimlab-wustl.github.io/RCNteststation/docs/subsystems/dac/characterization) and [ADC characterization](https://aimlab-wustl.github.io/RCNteststation/docs/subsystems/adc/characterization) pages report measured board-level performance together with the conditions and limitations of each test.

The [Adaptive AC analysis](https://aimlab-wustl.github.io/RCNteststation/docs/automation/adaptive-ac) page demonstrates an Ax-based Bayesian optimization workflow that adaptively selects frequency points to estimate gain, phase, and −3 dB bandwidth with fewer physical measurements.

## Repository contents

| Path | Contents |
| --- | --- |
| [`pcb/`](pcb/) | V3 motherboard schematic and PCB, daughterboard PCB, and fabrication packages |
| [`firmware/`](firmware/) | STM32 firmware and required vendor libraries |
| [`python/`](python/) | Hardware drivers and measurement scripts |
| [`website/test-station/`](website/test-station/) | System documentation, schematics, and characterization figures |

## Status

MOSFET and op-amp DC measurements, fast step-response capture, and adaptive AC characterization have been implemented. The adaptive AC pipeline has been experimentally demonstrated using Gaussian-process-based Bayesian optimization to select measurement frequencies efficiently.

Noise characterization, adaptive PSRR testing, and the broader automated test-planning layer remain under development. The system is intended to support different post-tapeout devices through interchangeable DUT adapters and reusable measurement routines.

## Credit and license

Project development: **Kaiyuan (Sam) Kang**, AIMLAB, Washington University in St. Louis.

Unless otherwise noted, original project material is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International Public License](LICENSE) (**CC BY-NC 4.0**). Noncommercial reuse and adaptation require attribution, a link to the license, and an indication of changes. Commercial use requires separate permission from the rights holder. Third-party STM32 libraries retain their own licenses in their respective directories.