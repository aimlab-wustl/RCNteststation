"""
measurements/ib.py
===================
Input bias current (Ib+, Ib-) for the op-amp DUT, using the TIA
(hardware.tia.TIA, wraps OPA3S328 amp B + ADS131A04 chip2/ch4).

PHYSICAL SETUP -- see wiring diagram in chat. Summary:
    Ib+ : A+ -> TIA -INB (lift off DAC80508 Ch1)
          A- -> Vref node directly (lift off Rf/Rg)
          Aout: leave floating -- no closed loop needed for this test,
          Aout may rail, that's expected and harmless.
    Ib- : mirror image -- A- -> TIA -INB, A+ -> Vref (can stay on the
          DAC, just hold it at Vref in software instead of rewiring).

This is a genuinely different fixture topology than dc.py's closed-loop
sweep -- don't run this concurrently with a DCTest instance. Power down
V+ before each rewire, back up after, same discipline as elsewhere in
this project.

Uses the B_2M range (2Mohm feedback, +/-1uA full scale) -- the most
sensitive available, appropriate for OPA4388's ~30pA typ / ~500pA max
spec. Whether that's actually resolvable depends on your calibration's
residual noise (printed by TIA on load) -- if it's comparable to or
larger than the expected signal, treat the result as an upper bound,
not a clean number.
"""

import os
import json
import time
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import sys
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))
import hardware.dac_dac80508 as dacmod
from hardware.tia import TIA

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class IbTest:
    def __init__(self, dac_num=1, dac_ch=1, vref=2.5, tag="opa4388",
                 tia_range="B_2M", n_avg=512):
        self.dac_num = dac_num
        self.dac_ch = dac_ch
        self.vref = vref
        self.tag = tag
        self.n_avg = n_avg
        self.results = {}

        # Hold the DAC at Vref throughout -- relevant only for the Ib-
        # sub-test, where A+ stays physically on this DAC channel.
        # Harmless during Ib+ (A+ is physically disconnected from it then).
        dacmod.initialize()
        dacmod.set_voltage(self.dac_num, self.dac_ch, self.vref)

        self.tia = TIA()             # loads existing tia_cal.json
        self.tia.set_range(tia_range)
        print(f"[Ib] Using {tia_range}, Rf_eff={self.tia._rf:.0f} ohm, "
              f"+/-{self.tia.full_scale_uA:.2f}uA full scale")

    def _wait_for_stable(self, batch_n=100, tol_pA=50.0, window=5, max_batches=60):
        """
        Same idea as dc.py's ADC-flush fix: keep reading batches until
        several consecutive batch means agree, instead of trusting that
        enough real time has passed. Cheap insurance -- run before every
        recorded measurement, not just after a known-big transition.
        """
        means = []
        for _ in range(max_batches):
            m = self.tia.stats(n=batch_n)["mean_uA"] * 1e6
            means.append(m)
            if len(means) >= window and (max(means[-window:]) - min(means[-window:])) < tol_pA:
                return
        print("[Ib] WARNING: did not fully stabilize within max_batches -- "
              "reading may still be settling.")

    def _measure(self, label):
        self._wait_for_stable()
        s = self.tia.stats(n=self.n_avg)
        mean_pA = s["mean_uA"] * 1e6
        std_pA = s["std_nA"] * 1000
        print(f"[Ib] {label}: {mean_pA:+.2f} pA  (std {std_pA:.2f} pA, "
              f"n={s['n']})")
        return {"mean_pA": mean_pA, "std_pA": std_pA, "n": s["n"],
                "range": s["range"]}

    def run_both(self):
        input("\nSet up Ib+ config: A+ -> TIA -INB, A- -> Vref node "
              "directly (Rf/Rg lifted). Aout left floating.\n"
              "Bring V+ back up, then press ENTER...")
        self.results["ib_plus"] = self._measure("Ib+")

        input("\nNow swap to Ib- config: A- -> TIA -INB, A+ -> Vref "
              "(already held there by the DAC). Aout left floating.\n"
              "Power down V+ before rewiring, back up after, then "
              "press ENTER...")
        self.results["ib_minus"] = self._measure("Ib-")

        ib_plus = self.results["ib_plus"]["mean_pA"]
        ib_minus = self.results["ib_minus"]["mean_pA"]
        self.results["ios_pA"] = ib_plus - ib_minus   # input offset current
        print(f"\n[Ib] Summary: Ib+={ib_plus:+.2f}pA  Ib-={ib_minus:+.2f}pA  "
              f"Ios={self.results['ios_pA']:+.2f}pA")
        print("     Datasheet (OPA4388): Ib ~30pA typ / 500pA max, "
              "Ios <=1000pA max -- compare against that, and against "
              "this measurement's own std to judge if it's a real "
              "number or floor-limited.")

        self.save()
        return self.results

    def save(self):
        path = os.path.join(SCRIPT_DIR, f"ib_{self.tag}.json")
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"    saved {path}")


if __name__ == "__main__":
    ib = IbTest(dac_num=1, dac_ch=1, tag="opa4388")
    try:
        ib.run_both()
    finally:
        dacmod.clear_all()