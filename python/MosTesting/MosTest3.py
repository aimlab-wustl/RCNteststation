# test3_final.py
# SI2302CDS — Test 3 Final: Body diode (Vsd vs Is)
#
# Circuit:
#   AO ch1  ──────── Drain (pin3) ── AI ch0   (hard 0V, direct)
#   DAC CH2 ──────── Gate  (pin1) ── AI ch2   (0V, channel off)
#   DAC CH1 ──────── Source (pin2)── AI ch1
#                                 └─ 10kΩ ─── GND
#
# Is_measured = V_source / R_shunt = shunt current
# Since shunt (10kΩ) and body diode are in parallel from source to drain/GND:
#   Is_shunt  = V_source / 10kΩ
#   Is_diode  = Is_shunt × (V_source > Vf)   ← only when diode conducting
#
# True diode current = DAC current − shunt current
# We don't measure DAC current directly, but:
#   I_dac ≈ (V_dac_cmd − V_source) / R_dac_output  [R_dac very small]
# So we can't separate them perfectly.
#
# PRACTICAL INTERPRETATION:
#   Plot Vsd vs Is_shunt as a proxy for the diode curve.
#   Vf is extracted where the curve departs from the linear shunt behaviour.
#   The departure point = where diode starts conducting significantly.
#
# Saves:
#   test3_raw_<timestamp>.csv
#   test3_summary_<timestamp>.json
#   test3_final_<timestamp>.png

import time
import json
import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hardware import dac_initialize, set_voltage, dac_clear_all
from hardware import write_single as ao_write, zero_all as ao_zero

# ── Config ────────────────────────────────────────────────────
DEVICE      = "Dev1"
R_SHUNT     = 10_000.0   # 10kΩ — measure with DMM and update
SETTLE      = 0.10
N_AVG       = 64
AO_DRAIN_CH = 1

# Cap at 1.2V to avoid fold-back (shunt drop = 1.2V/10kΩ × 10kΩ = 1.2V
# leaves 0V headroom — so stay well below that)
# At 1.0V: shunt current = 1.0/10k = 100µA, shunt drop = 1.0V, Vsd ≈ 0V
# Better cap: 0.8V so shunt drops 800mV max, Vsd can reach ~600mV
# Actually: V_dac = Vsd + V_shunt = Vsd + Is×10kΩ
# At Vf=600mV, Is≈80µA → V_shunt=800mV → V_dac needed = 1.4V ← ok
DAC_SOURCE_MAX   = 1.4
DAC_SOURCE_STEPS = 101   # more points for better curve resolution

VF_IS = 50e-6    # extraction threshold

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE  = os.path.join(SCRIPT_DIR, f"test3_raw_{TIMESTAMP}.csv")
JSON_FILE = os.path.join(SCRIPT_DIR, f"test3_summary_{TIMESTAMP}.json")
PNG_FILE  = os.path.join(SCRIPT_DIR, f"test3_final_{TIMESTAMP}.png")

# ── AI read ───────────────────────────────────────────────────
def read_ai():
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai0", terminal_config=TerminalConfiguration.RSE,
            min_val=-10.0, max_val=10.0,
        )
        t.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai1", terminal_config=TerminalConfiguration.RSE,
            min_val=-1.0, max_val=1.0,     # V_source max ~1.4V — use ±10V
        )
        t.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai2", terminal_config=TerminalConfiguration.RSE,
            min_val=-10.0, max_val=10.0,
        )
        t.timing.cfg_samp_clk_timing(rate=10_000, samps_per_chan=N_AVG)
        raw = t.read(number_of_samples_per_channel=N_AVG)
        return [sum(ch) / len(ch) for ch in raw]

# ── Measurement ───────────────────────────────────────────────
print("="*60)
print("  Test 3 Final — Body diode (Vsd vs Is)")
print("="*60)
print()
print("  CIRCUIT:")
print("  ✓ AO ch1  → Drain (pin3) directly")
print("  ✓ DAC CH1 → Source (pin2)")
print("  ✓ DAC CH2 → Gate (pin1) = 0V")
print(f"  ✓ {R_SHUNT/1000:.0f}kΩ shunt: Source → GND")
print()
input("  Press ENTER to start...")

dac_initialize()
ao_zero()
ao_write(AO_DRAIN_CH, 0.0)
set_voltage(1, 2, 0.0)
set_voltage(1, 1, 0.0)
time.sleep(0.3)

source_sweep = np.linspace(0.0, DAC_SOURCE_MAX, DAC_SOURCE_STEPS)
Vsd_arr, Is_arr, Vs_arr = [], [], []
all_rows = []

for i, vs_cmd in enumerate(source_sweep):
    set_voltage(1, 1, vs_cmd)
    time.sleep(SETTLE)
    v_drain, v_source, v_gate = read_ai()
    Is  = v_source / R_SHUNT
    Vsd = v_source - v_drain

    Vsd_arr.append(Vsd)
    Is_arr.append(Is)
    Vs_arr.append(v_source)
    all_rows.append({
        "dac_cmd_V": round(vs_cmd,   4),
        "V_drain":   round(v_drain,  6),
        "V_source":  round(v_source, 6),
        "V_gate":    round(v_gate,   6),
        "Vsd_V":     round(Vsd,      6),
        "Is_A":      round(Is,       9),
    })
    if i % 25 == 0:
        print(f"  [{i+1:3d}/{DAC_SOURCE_STEPS}]  "
              f"DAC={vs_cmd:.3f}V  Vsd={Vsd*1000:.1f}mV  Is={Is*1e6:.1f}µA")

set_voltage(1, 1, 0.0)
ao_zero()
dac_clear_all()

Vsd_arr = np.array(Vsd_arr)
Is_arr  = np.array(Is_arr)
Vs_arr  = np.array(Vs_arr)

# ── Save CSV ──────────────────────────────────────────────────
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
    writer.writeheader()
    writer.writerows(all_rows)
print(f"\n  Saved → {CSV_FILE}  ({len(all_rows)} rows)")

# ── Trim fold-back: keep only the forward sweep (Vsd increasing) ──
# Find where Vsd peaks and truncate there
peak_idx = int(np.argmax(Vsd_arr))
Vsd_arr  = Vsd_arr[:peak_idx+1]
Is_arr   = Is_arr[:peak_idx+1]
Vs_arr   = Vs_arr[:peak_idx+1]

# ── Extract Vf at Is = 50µA ───────────────────────────────────
vf = None
for i in range(len(Is_arr) - 1):
    if Is_arr[i] < VF_IS <= Is_arr[i+1]:
        frac = (VF_IS - Is_arr[i]) / (Is_arr[i+1] - Is_arr[i])
        vf   = float(Vsd_arr[i] + frac * (Vsd_arr[i+1] - Vsd_arr[i]))
        break

# ── Ideality factor from log(Is) vs Vsd ──────────────────────
# Fit in 5µA → 45µA window — avoids noise floor and fold-back region
Vt = 0.02585
exp_mask = (Is_arr > 5e-6) & (Is_arr < 45e-6)
n_ideality = None
if exp_mask.sum() > 5:
    try:
        slope      = np.polyfit(Vsd_arr[exp_mask],
                                np.log(Is_arr[exp_mask]), 1)
        n_ideality = 1.0 / (slope[0] * Vt)
    except Exception:
        pass

# ── Results ───────────────────────────────────────────────────
print()
print("="*60)
print("  Results")
print("="*60)
if vf:
    in_spec = vf < 1.2
    print(f"  Vf @ Is=50µA  = {vf*1000:.1f} mV  "
          f"(spec <1200mV @ 0.95A)  {'PASS ✓' if in_spec else 'FAIL ✗'}")
    print(f"  Note: datasheet Vf=700mV is at Is=0.95A — lower Is → lower Vf")
else:
    print("  Vf: Is never reached 50µA — check wiring")
print(f"  Max Is  = {max(Is_arr)*1e6:.1f} µA  "
      f"at Vsd = {Vsd_arr[np.argmax(Is_arr)]*1000:.1f} mV")
if n_ideality:
    n_comment = ("good — typical body diode" if 1.5 <= n_ideality <= 2.5
                 else "high — shunt resistor distorting fit")
    print(f"  Ideality n ≈ {n_ideality:.2f}  ({n_comment})")
print("="*60)

# ── Save JSON ─────────────────────────────────────────────────
summary = {
    "timestamp":     TIMESTAMP,
    "device":        "SI2302CDS",
    "R_shunt_ohm":   R_SHUNT,
    "Vf_at_50uA_mV": round(vf * 1000, 1) if vf else None,
    "Vf_pass":       bool(vf < 1.2) if vf else None,
    "max_Is_uA":     round(max(Is_arr) * 1e6, 2),
    "ideality_n":    round(n_ideality, 3) if n_ideality else None,
}
with open(JSON_FILE, "w") as f:
    json.dump(summary, f, indent=2)
print(f"  Saved → {JSON_FILE}")

# ── Plot ──────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
fig.suptitle("SI2302CDS — Test 3: Body diode (Vsd vs Is)", fontsize=11)

ax = axes[0]
ax.plot(Vsd_arr * 1000, Is_arr * 1e6, color="darkorange", lw=1.5)
# Overlay the pure shunt line for reference (what the curve would look like
# if only the shunt conducted and the diode didn't exist)
vsd_ref = np.linspace(0, max(Vsd_arr) * 1000, 100)
Is_shunt_ref = vsd_ref / (R_SHUNT * 1000 / 1000)  # µA — shunt only
# shunt current at Vsd: if all voltage across shunt = Vsd, Is = Vsd/R_shunt
# but that's not right either since shunt is from source to GND not Vsd
# Just skip the reference line — it would be confusing
if vf:
    ax.axvline(vf * 1000, color="red", ls="--", lw=1,
               label=f"Vf = {vf*1000:.0f} mV @ 50µA")
    ax.axhline(VF_IS * 1e6, color="gray", ls=":", lw=0.8,
               label="Is = 50µA")
    ax.legend(fontsize=8)
ax.set_xlabel("Vsd (mV)"); ax.set_ylabel("Is (µA)")
ax.set_title("Body diode — linear")
ax.set_xlim(left=0); ax.set_ylim(bottom=-1)
ax.grid(True, alpha=0.4)

ax = axes[1]
valid = Is_arr > 1e-9
ax.semilogy(Vsd_arr[valid] * 1000, Is_arr[valid] * 1e6,
            color="darkorange", lw=1.5)
# Overlay ideality fit line
if n_ideality and exp_mask.sum() > 5:
    vsd_fit = np.linspace(Vsd_arr[exp_mask][0],
                          Vsd_arr[exp_mask][-1], 50)
    # reconstruct fit: log(Is) = slope × Vsd + intercept
    coeffs   = np.polyfit(Vsd_arr[exp_mask],
                          np.log(Is_arr[exp_mask]), 1)
    Is_fit   = np.exp(np.polyval(coeffs, vsd_fit)) * 1e6
    ax.semilogy(vsd_fit * 1000, Is_fit, color="steelblue",
                ls="--", lw=1, label=f"fit  n={n_ideality:.2f}")
if vf:
    ax.axvline(vf * 1000, color="red", ls="--", lw=1,
               label=f"Vf = {vf*1000:.0f} mV")
ax.legend(fontsize=8)
ax.set_xlabel("Vsd (mV)"); ax.set_ylabel("Is (µA)  [log]")
ax.set_title("Body diode — log scale + ideality fit")
ax.set_xlim(left=0)
ax.grid(True, alpha=0.4, which="both")

plt.tight_layout()
plt.savefig(PNG_FILE, dpi=150)
plt.show()
print(f"  Saved → {PNG_FILE}")
print("\n  Test 3 complete.")