"""
measurements/psrr_dc.py
========================
DC PSRR for the op-amp DUT: hold Vin=Vref (so Aout should ideally stay
exactly at Vref regardless of Rf/Rg, same trick dc.py uses to extract
Vos), then step V+ with the Keithley 2450 and watch how much Aout
moves. The slope dAout/dV+, divided by the closed-loop gain, gives the
input-referred PSRR.

PHYSICAL SETUP -- same gain-11 fixture as dc.py, ONE change:
    V+ source: Keithley 2450 HI -> OPA4388 V+ pin (replaces bench
               supply -- disconnect the bench supply from V+ entirely,
               don't leave two sources fighting the same node)
               Keithley 2450 LO -> common AGND
    Everything else UNCHANGED from dc.py: A+ on DAC80508 ch1/1 (held
    at Vref, not swept), Rf/Rg/Vref feedback network intact, ADC
    differential against Vref, unused channels still tied off.

CAVEAT -- confirm before trusting the number: does the ADR4525
reference share the SAME physical supply rail as V+ (the one being
swept here), or does it have its own independent supply? If shared,
this measurement mixes the DUT's real PSRR with the reference's own
(small, but non-zero) supply sensitivity.

Sweep defaults to a SAFE, modest window around nominal (4.5-5.5V)
rather than the full 2.5-5.5V datasheet range -- widen later once
this runs clean once. Current limit set conservatively (50mA) as
fault protection, well above the ~10mA nominal quad-chip load.

Power sequencing: Keithley comes up to nominal V+ BEFORE the DAC is
commanded to Vref; DAC is zeroed BEFORE V+ is brought back down.
Same discipline as everywhere else in this project.

Every point in this (short, 11-point) sweep is fully flushed via
_wait_for_stable() unconditionally -- PSRR is a uV-scale measurement,
so it's worth paying the settle cost on every point rather than only
after "big" transitions like the DC/CMR scripts do.
"""

import os
import csv
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import pyvisa

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import sys
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

import hardware.dac_dac80508 as dacmod
from hardware.ads131a04 import ADS131

KEITHLEY_ADDR = "USB0::0x05E6::0x2450::04345889::INSTR"


class PSRRDCTest:
    def __init__(self, dac_num=1, dac_ch=1, adc_chip=1, adc_ch=1,
                 vref=2.5, vpos_nom=5.0, settle_s=0.6, n_avg=256,
                 gain=10.86, tag="opa4388", adc: ADS131 = None,
                 keithley_addr=KEITHLEY_ADDR, i_limit_A=0.05):
        self.dac_num = dac_num
        self.dac_ch = dac_ch
        self.adc_chip = adc_chip
        self.adc_ch = adc_ch
        self.vref = vref
        self.vpos_nom = vpos_nom
        self.settle_s = settle_s
        self.n_avg = n_avg
        self.gain = gain     # measured closed-loop gain from dc.py, for
                              # converting output-referred slope to input-referred
        self.tag = tag
        self.results = {}

        dacmod.initialize()
        self.adc = adc if adc is not None else ADS131()

        print(f"[PSRR] Connecting to Keithley {keithley_addr}...")
        rm = pyvisa.ResourceManager()
        self.keith = rm.open_resource(keithley_addr)
        self.keith.timeout = 10000
        self.keith.write("*RST")
        time.sleep(1.0)
        print(f"[PSRR]   {self.keith.query('*IDN?').strip()}")

        self.keith.write("SOUR:FUNC VOLT")
        self.keith.write(f"SOUR:VOLT:ILIM {i_limit_A:.4f}")
        self.keith.write('SENS:FUNC "CURR"')
        self.keith.write("SENS:CURR:RANG 0.1")

        # power up at nominal BEFORE commanding the DAC input
        self.keith.write(f"SOUR:VOLT {vpos_nom:.4f}")
        self.keith.write("OUTP ON")
        time.sleep(0.5)
        dacmod.set_voltage(self.dac_num, self.dac_ch, self.vref)
        print(f"[PSRR] V+ = {vpos_nom:.3f}V (Keithley), Vin = Vref = "
              f"{self.vref:.3f}V")

    def _set_vpos(self, v):
        self.keith.write(f"SOUR:VOLT {v:.4f}")

    def _adc_read_n(self, n):
        v_arr, _t = self.adc.read_buffered(chip=self.adc_chip, num_frames=n)
        ch_row = v_arr[self.adc_ch - 1]
        return ch_row + self.vref

    def _wait_for_stable(self, batch_n=100, tol_v=2e-5, window=5, max_batches=120):
        """Same convergence-based flush as dc.py/cmr.py."""
        means, row = [], None
        for _ in range(max_batches):
            v_arr, _t = self.adc.read_buffered(chip=self.adc_chip, num_frames=batch_n)
            row = v_arr[self.adc_ch - 1]
            means.append(float(np.mean(row)))
            if len(means) >= window and (max(means[-window:]) - min(means[-window:])) < tol_v:
                return row
        return row

    def _measure_point(self, vpos):
        self._set_vpos(vpos)
        time.sleep(self.settle_s)
        self._wait_for_stable()
        s = self._adc_read_n(self.n_avg)
        return float(np.mean(s)), float(np.std(s))

    def sweep(self, vpos_lo=4.5, vpos_hi=5.5, n=11, fit_vpos_lo=5.0):
        """
        fit_vpos_lo: only fit the slope using points at/above this V+.
        Default 5.0 -- the first pass at this fixture showed a real,
        reproducible knee below ~5.0V (not a settling artifact -- ruled
        out by testing 12x longer settle time with no change in result),
        so fitting the full 4.5-5.5V range understates PSRR by mixing
        the knee region into what should be a straight-line fit. The
        full sweep is still recorded and plotted either way -- only the
        fit is restricted.
        """
        vpos = np.linspace(vpos_lo, vpos_hi, n)
        pts = [self._measure_point(v) for v in vpos]
        aout = np.array([p[0] for p in pts])
        astd = np.array([p[1] for p in pts])
        err = aout - self.vref   # deviation from ideal (Aout should == Vref)

        fit_mask = vpos >= fit_vpos_lo
        if fit_mask.sum() < 2:
            fit_mask = np.ones_like(vpos, dtype=bool)   # fall back to full sweep
        vpos_fit, aout_fit, astd_fit = vpos[fit_mask], aout[fit_mask], astd[fit_mask]

        slope_out, intercept = np.polyfit(vpos_fit, aout_fit, 1)   # V/V, output-referred
        slope_in = slope_out / self.gain                            # V/V, input-referred
        psrr_db = (20 * np.log10(1.0 / abs(slope_in))
                   if slope_in != 0 else float("inf"))

        # rough 1-sigma uncertainty on the dB figure, from per-point
        # standard error of the mean and the fit's x-spread
        se_per_point = float(np.mean(astd_fit)) / np.sqrt(self.n_avg)
        ss_x = float(np.sum((vpos_fit - vpos_fit.mean()) ** 2))
        se_slope_out = se_per_point / np.sqrt(ss_x) if ss_x > 0 else float("nan")
        rel_err = (se_slope_out / abs(slope_out)
                   if slope_out != 0 and not np.isnan(se_slope_out) else float("nan"))
        psrr_db_unc = (20 * np.log10(1 + rel_err)
                       if not np.isnan(rel_err) and rel_err < 1 else float("nan"))

        self.keith.write(f"SOUR:VOLT {self.vpos_nom:.4f}")   # back to nominal

        self.results["psrr_dc"] = {
            "vpos": vpos.tolist(), "aout": aout.tolist(),
            "aout_std": astd.tolist(), "err_V": err.tolist(),
            "fit_vpos_lo": fit_vpos_lo, "n_fit_points": int(fit_mask.sum()),
            "slope_output_V_per_V": float(slope_out),
            "slope_input_referred_V_per_V": float(slope_in),
            "gain_used": self.gain,
            "psrr_dB": float(psrr_db),
            "psrr_dB_uncertainty_1sigma": float(psrr_db_unc),
            "vref": self.vref,
        }
        print(f"[PSRR] fit uses {fit_mask.sum()}/{n} points (V+ >= "
              f"{fit_vpos_lo}V)")
        print(f"[PSRR] output-referred slope = {slope_out*1e6:.2f} uV/V")
        print(f"[PSRR] input-referred slope  = {slope_in*1e9:.2f} nV/V  "
              f"(using gain={self.gain})")
        print(f"[PSRR] PSRR = {psrr_db:.1f} +/- {psrr_db_unc:.1f} dB (1-sigma)")
        return self.results["psrr_dc"]

    def run_all(self):
        self.sweep()
        self.save()
        self.plot()
        return self.results

    def save(self):
        base = os.path.join(SCRIPT_DIR, f"psrr_dc_{self.tag}")
        with open(base + ".json", "w") as f:
            json.dump(self.results, f, indent=2)
        p = self.results.get("psrr_dc")
        if p:
            with open(base + ".csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["vpos_V", "aout_V", "aout_std_V", "err_V"])
                for row in zip(p["vpos"], p["aout"], p["aout_std"], p["err_V"]):
                    w.writerow(row)
        print(f"    saved {base}.json / .csv")

    def plot(self):
        p = self.results.get("psrr_dc")
        if not p:
            return
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(p["vpos"], np.array(p["err_V"]) * 1e6, ".-")
        ax.set(xlabel="V+ (V)", ylabel="Aout - Vref (uV)",
               title=f"{self.tag}  DC PSRR = {p['psrr_dB']:.1f}dB "
                     f"(input-referred, gain={p['gain_used']})")
        fig.tight_layout()
        out = os.path.join(SCRIPT_DIR, f"psrr_dc_{self.tag}.png")
        fig.savefig(out, dpi=120)
        print(f"    saved {out}")

    def close(self):
        """Zero the DAC BEFORE bringing V+ down -- same power-down
        discipline as everywhere else in this project."""
        dacmod.set_voltage(self.dac_num, self.dac_ch, 0.0)
        time.sleep(0.05)
        self.keith.write(f"SOUR:VOLT {self.vpos_nom:.4f}")
        time.sleep(0.2)
        self.keith.write("OUTP OFF")
        self.keith.close()


if __name__ == "__main__":
    psrr = PSRRDCTest(dac_num=1, dac_ch=1, adc_chip=1, adc_ch=1, tag="opa4388")
    try:
        psrr.run_all()
    finally:
        psrr.close()
        dacmod.clear_all()