---
id: measurements-overview
title: Measurements Overview
sidebar_position: 1
---

# Measurements Overview

## Overview

The test station provides automated measurement pipelines for characterizing analog ICs.
Each pipeline runs from Python, saves timestamped outputs, and is designed to be reused
across different DUTs by changing a small set of parameters at instantiation.

Depending on the pipeline, measurements combine the DAC80508 and NI USB-6212
for bias generation and low-speed acquisition, the ADS131A04 for precision
voltage acquisition, the OPA3S328 TIA for current measurement, and the STM32
internal ADC for transient capture.

## Available Pipelines

| Pipeline | Script | Extracts | Status |
|----------|--------|---------|--------|
| [MOSFET -- Transfer curve](./mosfet/mosfet-overview#test-1----transfer-curve-id-vs-vgs) | `MosTest12.py` | Vth, peak gm, max Id | Implemented |
| [MOSFET -- Output characteristics](./mosfet/mosfet-overview#test-2----output-characteristics-id-vs-vds) | `MosTest12.py` | Id-Vds family, Id_sat, RDS(on) | Implemented |
| [MOSFET -- Body diode](./mosfet/mosfet-overview#test-3----body-diode-vsd-vs-is) | `MosTest3.py` | Vf, ideality factor n | Implemented |
| [Op-Amp -- DC](./opamp/opamp-overview#dc-characterization-opa_dcpy----dctest) | `OPA_DC.py` | Gain, Vos, INL, output swing, noise floor | Implemented |
| [Op-Amp -- CMR](./opamp/opamp-overview#common-mode-range-opa_cmrpy----cmrtest) | `OPA_cmr.py` | Common-mode input range | Implemented |
| [Op-Amp -- DC PSRR](./opamp/opamp-overview#dc-psrr-opa_psrrpy----psrrtest) | `OPA_psrr.py` | DC power supply rejection | Implemented |
| [Op-Amp -- Input bias current](./opamp/opamp-overview#input-bias-current-opa_ibpy----ibtest) | `OPA_Ib.py` | Ib+, Ib-, Ios | Implemented |
| [Op-Amp -- Step response](./opamp/opamp-overview#step-response-steptestpy) | `steptest.py` | Slew rate, rise time, overshoot | Implemented |
| Op-Amp -- AC Bode | — | Gain + phase vs frequency, bandwidth | In progress |
| Op-Amp -- Noise PSD | — | Input-referred noise spectral density | In progress |

## Output Files

Outputs are saved next to the script, prefixed with the `tag` parameter.

**MOSFET pipeline** -- three files per test run, timestamped:

| File | Contents |
|------|---------|
| `test1_raw_*.csv` | Vgs, Vds, Id per sweep point |
| `test1_summary_*.json` | Vth, gm, pass/fail |
| `test1_final_*.png` | Transfer curve (linear + log) |
| `test2_raw_*.csv` | Id-Vds per Vgs curve |
| `test2_summary_*.json` | Id_sat, RDS(on) per Vgs |
| `test2_final_*.png` | Output curves + knee zoom + bar chart |
| `test3_raw_*.csv` | Vsd, Is per sweep point |
| `test3_summary_*.json` | Vf, ideality n, pass/fail |
| `test3_final_*.png` | Body diode (linear + log + fit) |

**Op-amp pipeline** -- per test:

| File | Contents |
|------|---------|
| `dc_{tag}.json` | Baseline, coarse, fine sweep results |
| `dc_{tag}_fine.csv` | Vin, Aout, std, residual (fine sweep) |
| `dc_{tag}.png` | Coarse sweep + INL residual plot |
| `cmr_{tag}.json` | CMR sweep results |
| `cmr_{tag}.csv` | Vin, Aout, error per point |
| `cmr_{tag}.png` | Unity-gain sweep + error plot |
| `psrr_dc_{tag}.json` | PSRR sweep results |
| `psrr_dc_{tag}.csv` | V+, Aout, input-referred error |
| `psrr_dc_{tag}.png` | PSRR vs V+ plot |
| `ib_{tag}.json` | Ib+, Ib-, Ios in pA |
| `{tag}_step_response.npz` | Raw ADC samples + time axis |
| `{tag}_step_response.mat` | Same in MATLAB format |
| `{tag}_step_response_metrics.json` | Slew rate, rise time, overshoot, settling |
| `{tag}_step_response.png` | Full capture + zoomed plot |