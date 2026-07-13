"""
measurements/cmr.py
====================
Common-mode input range (CMR) for the op-amp DUT.

PHYSICAL SETUP -- DIFFERENT topology than dc.py's gain-11 sweep.
    Unity-gain buffer required so Aout can track the FULL 0..5V input
    range without hitting output clipping at gain=11 (dc.py's coarse
    sweep already showed only ~2.28-2.72V of input survives at gain
    11 -- that's an OUTPUT swing limit, not the INPUT CMR limit this
    script is after).

    Lift Rf (100k) and Rg (10k) off the A- pin entirely.
    Tie A- directly to Aout with a short wire (gain = 1).
    A+  : DAC80508 dac_num/dac_ch, swept 0..Vpos (full range this
          time, not centered on Vref like dc.py).
    ADC : unchanged from dc.py -- AINP=Aout, AINN=Vref. The Vref node
          itself is NOT used as a DUT input in this test (no Rg to
          feed it into), only as the ADC's differential reference.
    Power sequencing: same discipline as always -- V+ down before the
    Rf/Rg rewire, back up after.

With A-=A+=Vin (unity feedback) and Aout=A- ideally, expect Aout==Vin
across the whole sweep. Where that breaks down -- either the input
stage losing common-mode range near a rail, or the output stage's own
swing limit (OPA4388 is genuine RRIO, so expect these two effects to
coincide near the rails rather than show up separately) -- shows up as
a growing error = Aout - Vin.

CAVEAT -- possible ADC range limit, not a DUT limit: Aout-Vref spans
roughly -2.5V to +2.5V across this sweep. Project notes disagree on
whether the ADS131A04's true differential full-scale is +/-4V or
closer to +/-2.44V -- if it's the latter, the extreme ends of this
sweep could clip the ADC itself, not the amplifier. Tell them apart:
real CMR/output-swing failure looks like a smooth, DUT-shaped
saturation curve; ADC clipping looks like the error abruptly pinning
at a flat, constant value right at the edges.

Reuses the settle/flush lesson from dc.py (which needed 4 iterations
to get right) from the start here rather than re-deriving it.
"""

import os
import csv
import json
import time
import numpy as np
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import sys
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

import hardware.dac_dac80508 as dacmod
from hardware.ads131a04 import ADS131


class CMRTest:
    def __init__(self, dac_num=1, dac_ch=1, adc_chip=1, adc_ch=1,
                 vref=2.5, vpos=5.0, settle_s=0.005, n_avg=64,
                 tag="opa4388", adc: ADS131 = None):
        self.dac_num = dac_num
        self.dac_ch = dac_ch
        self.adc_chip = adc_chip
        self.adc_ch = adc_ch
        self.vref = vref
        self.vpos = vpos
        self.settle_s = settle_s
        self.n_avg = n_avg
        self.tag = tag
        self.results = {}
        self._last_aout = None   # tracks whether we're coming out of saturation

        dacmod.initialize()
        self.adc = adc if adc is not None else ADS131()

    def _dac_set(self, volts):
        dacmod.set_voltage(self.dac_num, self.dac_ch, volts)

    def _adc_read_n(self, n):
        v_arr, _t = self.adc.read_buffered(chip=self.adc_chip, num_frames=n)
        ch_row = v_arr[self.adc_ch - 1]
        return ch_row + self.vref

    def _wait_for_stable(self, batch_n=100, tol_v=2e-5, window=5, max_batches=120):
        """Same convergence-based flush as dc.py -- see that file's
        header for why a fixed sleep or fixed flush count don't work."""
        means, row = [], None
        for _ in range(max_batches):
            v_arr, _t = self.adc.read_buffered(chip=self.adc_chip, num_frames=batch_n)
            row = v_arr[self.adc_ch - 1]
            means.append(float(np.mean(row)))
            if len(means) >= window and (max(means[-window:]) - min(means[-window:])) < tol_v:
                return row
        return row

    def _measure_point(self, vin):
        near_rail = (self._last_aout is not None and
                     (self._last_aout < 0.1 or self._last_aout > self.vpos - 0.1))
        self._dac_set(vin)
        time.sleep(self.settle_s)
        if near_rail:
            self._wait_for_stable()
        s = self._adc_read_n(self.n_avg)
        mean_v = float(np.mean(s))
        self._last_aout = mean_v
        return mean_v, float(np.std(s))

    def sweep(self, n=101, err_threshold_v=0.05):
        """
        Full 0..Vpos sweep at unity gain. Reports the Vin range where
        |Aout-Vin| stays under err_threshold_v -- the empirical
        CMR/output-swing boundary -- plus the typical error within
        that well-behaved region.
        """
        vin = np.linspace(0.0, self.vpos, n)
        self._dac_set(vin[0])
        time.sleep(self.settle_s)
        self._wait_for_stable()   # first point has no prior reading to
                                   # trigger near_rail -- flush unconditionally
        pts = [self._measure_point(v) for v in vin]
        aout = np.array([p[0] for p in pts])
        astd = np.array([p[1] for p in pts])
        err = aout - vin

        ok = np.abs(err) < err_threshold_v
        if ok.sum() >= 2:
            vin_ok = (float(vin[ok].min()), float(vin[ok].max()))
            err_ok_mean = float(np.mean(err[ok]))
            err_ok_rms = float(np.std(err[ok]))
        else:
            vin_ok = (None, None)
            err_ok_mean = err_ok_rms = float("nan")

        self.results["cmr"] = {
            "vin": vin.tolist(), "aout": aout.tolist(),
            "aout_std": astd.tolist(), "err_V": err.tolist(),
            "err_threshold_V": err_threshold_v,
            "vin_ok_range": vin_ok,
            "err_ok_mean_V": err_ok_mean,
            "err_ok_rms_V": err_ok_rms,
        }
        print(f"[CMR] Vin range within {err_threshold_v*1000:.0f}mV of ideal "
              f"(Aout=Vin): {vin_ok}")
        print(f"[CMR] Within that range: mean err={err_ok_mean*1e6:.1f}uV  "
              f"rms err={err_ok_rms*1e6:.1f}uV")
        print("[CMR] If the error PINS flat at a constant value right at "
              "the edges rather than curving smoothly, that's likely ADC "
              "clipping, not a real DUT limit -- see file header.")
        return self.results["cmr"]

    def run_all(self):
        self.sweep()
        self.save()
        self.plot()
        return self.results

    def save(self):
        base = os.path.join(SCRIPT_DIR, f"cmr_{self.tag}")
        with open(base + ".json", "w") as f:
            json.dump(self.results, f, indent=2)
        c = self.results.get("cmr")
        if c:
            with open(base + ".csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["vin_V", "aout_V", "aout_std_V", "err_V"])
                for row in zip(c["vin"], c["aout"], c["aout_std"], c["err_V"]):
                    w.writerow(row)
        print(f"    saved {base}.json / .csv")

    def plot(self):
        c = self.results.get("cmr")
        if not c:
            return
        fig, ax = plt.subplots(2, 1, figsize=(8, 8))
        ax[0].plot(c["vin"], c["aout"], ".-", label="measured")
        ax[0].plot([0, self.vpos], [0, self.vpos], "k:", label="ideal (Aout=Vin)")
        ax[0].set(xlabel="Vin (V)", ylabel="Aout (V)",
                  title=f"{self.tag}  CMR sweep, unity gain")
        ax[0].legend()

        ax[1].plot(c["vin"], np.array(c["err_V"]) * 1000, ".-")
        ax[1].axhline(c["err_threshold_V"] * 1000, ls=":", c="r")
        ax[1].axhline(-c["err_threshold_V"] * 1000, ls=":", c="r")
        ax[1].set(xlabel="Vin (V)", ylabel="error, Aout-Vin (mV)",
                  title=f"CMR boundary: {c['vin_ok_range']}")
        fig.tight_layout()
        out = os.path.join(SCRIPT_DIR, f"cmr_{self.tag}.png")
        fig.savefig(out, dpi=120)
        print(f"    saved {out}")


if __name__ == "__main__":
    cmr = CMRTest(dac_num=1, dac_ch=1, adc_chip=1, adc_ch=1, tag="opa4388")
    try:
        cmr.run_all()
    finally:
        dacmod.clear_all()