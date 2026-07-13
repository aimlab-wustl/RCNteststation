# test12_si2302cds.py
# SI2302CDS — Test 1 (Transfer curve) + Test 2 (Output curves)
#
# Circuit (same wiring for both tests — no rewiring between them):
#   NI AO ch1 ── 10kΩ ── Drain (pin3) ── AI ch0  (±10V)
#   DAC1 CH2  ────────── Gate  (pin1) ── AI ch2  (±10V)
#                         Source (pin2) ── AI ch1  (±1V)
#                                       ── 100Ω ── GND
#
# BEFORE RUNNING:
#   config.py → AO_VOLTAGE_RANGE = (0.0, 10.0)
#
# Flow:
#   1. Run Test 1 → extracts Vth, gm
#   2. Pause — confirm before Test 2
#   3. Run Test 2 → uses Vth from Test 1 for Vgs steps automatically
#
# Saves (timestamped, next to this script):
#   test1_raw_*.csv,     test1_summary_*.json,  test1_final_*.png
#   test2_raw_*.csv,     test2_summary_*.json,  test2_final_*.png

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import time
import json
import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
from hardware import dac_initialize, set_voltage, dac_clear_all
from hardware import write_single as ao_write, zero_all as ao_zero

# ══════════════════════════════════════════════════════════════
# SHARED CONFIG
# ══════════════════════════════════════════════════════════════
DEVICE      = "Dev1"
R_DRAIN     = 10_000.0   # ohms — measure with DMM and update
R_SHUNT     = 100.0      # ohms — measure with DMM and update
SETTLE      = 0.10       # seconds per point
N_AVG       = 64
AO_DRAIN_CH = 1

# ══════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════

def read_ai():
    """AI ch0 V_drain (±10V), ch1 V_source (±1V), ch2 V_gate (±10V)."""
    with nidaqmx.Task() as t:
        t.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai0", terminal_config=TerminalConfiguration.RSE,
            min_val=-10.0, max_val=10.0,
        )
        t.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai1", terminal_config=TerminalConfiguration.RSE,
            min_val=-1.0, max_val=1.0,
        )
        t.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai2", terminal_config=TerminalConfiguration.RSE,
            min_val=-10.0, max_val=10.0,
        )
        t.timing.cfg_samp_clk_timing(rate=10_000, samps_per_chan=N_AVG)
        raw = t.read(number_of_samples_per_channel=N_AVG)
        return [sum(ch) / len(ch) for ch in raw]


def set_gate(vgs_cmd):
    """Write gate and verify via AI ch2. Retries up to 3 times."""
    for attempt in range(3):
        set_voltage(1, 2, vgs_cmd)
        time.sleep(0.20)
        _, _, v_gate = read_ai()
        if abs(v_gate - vgs_cmd) < 0.05:
            return True
        print(f"  [warn] Gate verify failed attempt {attempt+1}: "
              f"cmd={vgs_cmd:.3f}V read={v_gate*1000:.1f}mV — retrying")
        time.sleep(0.20)
    print(f"  [ERROR] Gate failed to settle at {vgs_cmd:.3f}V")
    return False


def id_sat_from_tail(Id_arr, tail=10):
    return float(np.mean(Id_arr[-tail:]))


def save_csv(filepath, rows):
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved → {filepath}  ({len(rows)} rows)")


def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved → {filepath}")


# ══════════════════════════════════════════════════════════════
# TEST 1 — Transfer curve (Id vs Vgs)
# ══════════════════════════════════════════════════════════════

def run_test1():
    V_DRAIN   = 5.0
    VGS_START = 0.0
    VGS_STOP  = 2.5
    VGS_STEPS = 101
    VTH_ID  = 50e-6    # 50µA — reachable with this circuit

    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file  = os.path.join(SCRIPT_DIR, f"test1_raw_{ts}.csv")
    json_file = os.path.join(SCRIPT_DIR, f"test1_summary_{ts}.json")
    png_file  = os.path.join(SCRIPT_DIR, f"test1_final_{ts}.png")

    print("\n" + "="*55)
    print("  TEST 1 — Transfer curve (Id vs Vgs)")
    print("="*55)
    print(f"  Drain : NI AO ch{AO_DRAIN_CH} = {V_DRAIN}V fixed")
    print(f"  Gate  : DAC1 CH2  {VGS_START}→{VGS_STOP}V  ({VGS_STEPS} steps)")
    input("  Press ENTER to start Test 1...")

    ao_write(AO_DRAIN_CH, V_DRAIN)
    set_voltage(1, 2, 0.0)
    time.sleep(0.3)

    vgs_cmds = np.linspace(VGS_START, VGS_STOP, VGS_STEPS)
    Vgs_arr, Id_arr, Vds_arr = [], [], []
    rows = []

    for i, vgs_cmd in enumerate(vgs_cmds):
        set_voltage(1, 2, vgs_cmd)
        time.sleep(SETTLE)
        v_drain, v_source, v_gate = read_ai()
        Id  = v_source / R_SHUNT
        Vgs = v_gate  - v_source
        Vds = v_drain - v_source
        Vgs_arr.append(Vgs); Id_arr.append(Id); Vds_arr.append(Vds)
        rows.append({
            "vgs_cmd_V": round(vgs_cmd,  4),
            "V_drain":   round(v_drain,  6),
            "V_source":  round(v_source, 6),
            "V_gate":    round(v_gate,   6),
            "Vgs_V":     round(Vgs,      6),
            "Vds_V":     round(Vds,      6),
            "Id_A":      round(Id,       9),
        })
        if i % 20 == 0:
            print(f"  [{i+1:3d}/{VGS_STEPS}]  Vgs={Vgs*1000:.1f}mV  "
                  f"Id={Id*1e6:.2f}µA  Vds={Vds*1000:.1f}mV")

    ao_write(AO_DRAIN_CH, 0.0)
    set_voltage(1, 2, 0.0)

    Vgs_arr = np.array(Vgs_arr)
    Id_arr  = np.array(Id_arr)
    Vds_arr = np.array(Vds_arr)

    # Extract Vth
    vth = None
    for i in range(len(Id_arr) - 1):
        if Id_arr[i] < VTH_ID <= Id_arr[i+1]:
            frac = (VTH_ID - Id_arr[i]) / (Id_arr[i+1] - Id_arr[i])
            vth  = float(Vgs_arr[i] + frac * (Vgs_arr[i+1] - Vgs_arr[i]))
            break

    # Extract gm
    dId  = np.gradient(Id_arr, Vgs_arr)
    gm   = float(np.max(dId))
    gm_v = float(Vgs_arr[np.argmax(dId)])

    # Save
    save_csv(csv_file, rows)
    save_json(json_file, {
        "timestamp":   ts,
        "device":      "SI2302CDS",
        "R_drain_ohm": R_DRAIN,
        "R_shunt_ohm": R_SHUNT,
        "V_drain_V":   V_DRAIN,
        "Vth_V":       round(vth, 4) if vth else None,
        "Vth_pass":    bool(0.40 <= vth <= 0.85) if vth else None,
        "peak_gm_mS":  round(gm * 1000, 3),
        "gm_at_Vgs_V": round(gm_v, 4),
        "max_Id_uA":   round(max(Id_arr) * 1e6, 2),
    })

    # Print results
    print()
    print("="*55)
    print("  Test 1 Results")
    print("="*55)
    if vth:
        in_spec = 0.40 <= vth <= 0.85
        print(f"  Vth     = {vth*1000:.1f} mV  (spec 400–850mV)  "
              f"{'PASS ✓' if in_spec else 'FAIL ✗'}")
    else:
        print("  Vth     = not reached in sweep")
    print(f"  Peak gm = {gm*1000:.2f} mS  at Vgs={gm_v*1000:.1f}mV")
    print(f"  Max Id  = {max(Id_arr)*1e6:.1f} µA")
    print("="*55)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle("SI2302CDS — Test 1: Transfer curve", fontsize=11)

    ax = axes[0]
    ax.plot(Vgs_arr * 1000, Id_arr * 1e6, color="steelblue", lw=1.5)
    if vth:
        ax.axvline(vth * 1000, color="red", ls="--", lw=1,
                   label=f"Vth = {vth*1000:.0f} mV")
    ax.axhline(VTH_ID * 1e6, color="gray", ls=":", lw=0.8,
               label=f"Id = {VTH_ID*1e6:.0f} µA")
    ax.set_xlabel("Vgs (mV)"); ax.set_ylabel("Id (µA)")
    ax.set_title("Linear"); ax.legend(fontsize=8); ax.grid(True, alpha=0.4)

    ax = axes[1]
    ax.semilogy(Vgs_arr * 1000, np.maximum(Id_arr, 1e-9) * 1e6,
                color="steelblue", lw=1.5)
    if vth:
        ax.axvline(vth * 1000, color="red", ls="--", lw=1,
                   label=f"Vth = {vth*1000:.0f} mV")
    ax.set_xlabel("Vgs (mV)"); ax.set_ylabel("Id (µA) [log]")
    ax.set_title("Log scale"); ax.legend(fontsize=8)
    ax.grid(True, alpha=0.4, which="both")

    plt.tight_layout()
    plt.savefig(png_file, dpi=150)
    plt.show()
    print(f"  Saved → {png_file}")

    return vth


# ══════════════════════════════════════════════════════════════
# TEST 2 — Output curves (Id vs Vds)
# ══════════════════════════════════════════════════════════════

def run_test2(vth):
    V_DRAIN_MAX = 10.0

    if vth:
        vgs_steps = sorted(set([
            round(vth * 0.7,              2),
            round(vth,                    2),
            round(vth * 1.3,              2),
            round(vth * 1.8,              2),
            round(min(vth * 2.5, 2.5),    2),
            round(min(vth * 3.3, 2.5),    2),
        ]))
    else:
        vth = 0.662
        vgs_steps = [0.46, 0.66, 0.86, 1.19, 1.65, 2.20]

    vds_sweep = np.unique(np.concatenate([
        np.linspace(0.05, 0.5,  19),
        np.linspace(0.5,  V_DRAIN_MAX, 46),
    ]))

    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file  = os.path.join(SCRIPT_DIR, f"test2_raw_{ts}.csv")
    json_file = os.path.join(SCRIPT_DIR, f"test2_summary_{ts}.json")
    png_file  = os.path.join(SCRIPT_DIR, f"test2_final_{ts}.png")

    print("\n" + "="*55)
    print("  TEST 2 — Output curves (Id vs Vds)")
    print("="*55)
    print(f"  Vgs steps (from Vth={vth*1000:.0f}mV): {vgs_steps}")
    print(f"  Vds sweep: 50mV → {V_DRAIN_MAX*1000:.0f}mV  ({len(vds_sweep)} pts)")
    input("  Press ENTER to start Test 2...")

    all_curves = {}
    all_rows   = []

    for vgs_cmd in vgs_steps:
        print(f"  Vgs = {vgs_cmd:.2f}V", end="  ", flush=True)
        ao_write(AO_DRAIN_CH, 0.0)
        gate_ok = set_gate(vgs_cmd)
        time.sleep(0.20)

        Vds_row, Id_row = [], []
        for vd_cmd in vds_sweep:
            ao_write(AO_DRAIN_CH, vd_cmd)
            time.sleep(SETTLE)
            v_drain, v_source, v_gate = read_ai()
            Id  = v_source / R_SHUNT
            Vds = v_drain - v_source
            Vds_row.append(Vds); Id_row.append(Id)
            all_rows.append({
                "vgs_cmd_V": vgs_cmd,
                "V_drain":   round(v_drain,  6),
                "V_source":  round(v_source, 6),
                "V_gate":    round(v_gate,   6),
                "Vds_V":     round(Vds,      6),
                "Vgs_V":     round(v_gate - v_source, 6),
                "Id_A":      round(Id,       9),
            })

        ao_write(AO_DRAIN_CH, 0.0)
        time.sleep(0.15)
        all_curves[vgs_cmd] = (np.array(Vds_row), np.array(Id_row))
        print(f"Id_sat = {id_sat_from_tail(np.array(Id_row))*1e6:.1f} µA"
              + ("  [gate error]" if not gate_ok else ""))

    ao_zero()

    # Derived quantities
    id_ceiling = V_DRAIN_MAX / R_DRAIN * 1e6
    results = {}
    for vgs, (Vds_arr, Id_arr) in all_curves.items():
        id_sat   = id_sat_from_tail(Id_arr)
        above_th = vgs > (vth - 0.01)
        mask     = (Vds_arr > 0.005) & (Vds_arr < 0.05) & (Id_arr > 10e-6)
        rdson    = float(np.mean(
            np.clip(Vds_arr[mask], 0, None) / Id_arr[mask]
        )) if mask.sum() >= 3 else None
        sat_vds  = None
        if id_sat > 10e-6:
            for vds, id_ in zip(Vds_arr, Id_arr):
                if id_ >= 0.95 * id_sat and vds > 0.005:
                    sat_vds = vds; break
        results[vgs] = dict(id_sat=id_sat, rdson=rdson,
                            sat_vds=sat_vds, above_th=above_th)

    # Save
    save_csv(csv_file, all_rows)
    save_json(json_file, {
        "timestamp":   ts,
        "device":      "SI2302CDS",
        "R_drain_ohm": R_DRAIN,
        "R_shunt_ohm": R_SHUNT,
        "Vth_V":       vth,
        "curves": [
            {"Vgs_cmd_V":  vgs,
             "Id_sat_uA":  round(r["id_sat"] * 1e6, 2),
             "RDS_on_ohm": round(r["rdson"], 3) if r["rdson"] else None,
             "sat_Vds_mV": round(r["sat_vds"] * 1000, 1) if r["sat_vds"] else None,
             "above_Vth":  r["above_th"]}
            for vgs, r in results.items()
        ]
    })

    # Print results
    print()
    print("="*65)
    print("  Test 2 Results")
    print("="*65)
    print(f"  {'Vgs':>7}  {'Id_sat':>10}  {'RDS(on)':>10}  "
          f"{'Sat Vds':>10}  {'State':>10}")
    for vgs, r in results.items():
        rdson_s  = f"{r['rdson']:.1f} Ω"         if r['rdson']   else "n/a"
        satvds_s = f"{r['sat_vds']*1000:.0f} mV"  if r['sat_vds'] else "< 5mV"
        state    = "above Vth" if r['above_th'] else "below Vth"
        print(f"  {vgs:>7.2f}V  {r['id_sat']*1e6:>8.1f}µA  "
              f"{rdson_s:>10}  {satvds_s:>10}  {state}")
    print(f"  Circuit ceiling: {id_ceiling:.0f}µA")
    print("="*65)

    # Plot
    colors = plt.cm.plasma(np.linspace(0.15, 0.85, len(vgs_steps)))
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("SI2302CDS — Test 2: Output characteristics", fontsize=12)

    ax = axes[0]
    for (vgs, (Vds_arr, Id_arr)), color in zip(all_curves.items(), colors):
        r = results[vgs]
        ax.plot(Vds_arr * 1000, Id_arr * 1e6, color=color,
                lw=1.8 if r["above_th"] else 1.0,
                ls="-" if r["above_th"] else "--",
                label=f"Vgs={vgs:.2f}V {'▲' if r['above_th'] else '▽'}")
    ax.axhline(id_ceiling, color="gray", ls=":", lw=1, label="R_drain limit")
    ax.set_xlabel("Vds (mV)"); ax.set_ylabel("Id (µA)")
    ax.set_title("Full range (0–10V)")
    ax.set_xlim(0, V_DRAIN_MAX * 1000); ax.set_ylim(-50, id_ceiling * 1.15)
    ax.legend(fontsize=7.5, loc="lower right"); ax.grid(True, alpha=0.35)

    ax = axes[1]
    for (vgs, (Vds_arr, Id_arr)), color in zip(all_curves.items(), colors):
        r    = results[vgs]
        mask = Vds_arr <= 1.0
        ax.plot(Vds_arr[mask] * 1000, Id_arr[mask] * 1e6, color=color,
                lw=1.8 if r["above_th"] else 1.0,
                ls="-" if r["above_th"] else "--")
        if r["sat_vds"] and r["sat_vds"] <= 1.0:
            ax.axvline(r["sat_vds"] * 1000, color=color,
                       ls=":", lw=0.7, alpha=0.6)
            ax.annotate(f"{r['sat_vds']*1000:.0f}mV",
                        xy=(r["sat_vds"] * 1000 + 10, r["id_sat"] * 1e6 * 0.5),
                        fontsize=6.5, color=color)
    ax.axhline(id_ceiling, color="gray", ls=":", lw=1)
    ax.set_xlabel("Vds (mV)"); ax.set_ylabel("Id (µA)")
    ax.set_title("Knee zoom (0–1000mV)")
    ax.set_xlim(0, 1000); ax.set_ylim(-50, id_ceiling * 1.15)
    ax.grid(True, alpha=0.35)

    ax = axes[2]
    vgs_labels = [f"{v:.2f}" for v in vgs_steps]
    idsat_vals = [results[v]["id_sat"] * 1e6 for v in vgs_steps]
    bars = ax.bar(vgs_labels, idsat_vals, color=list(colors),
                  edgecolor="white", linewidth=0.5)
    for bar, vgs in zip(bars, vgs_steps):
        if not results[vgs]["above_th"]:
            bar.set_hatch("//"); bar.set_alpha(0.5)
    for bar, val in zip(bars, idsat_vals):
        if abs(val) > 5:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    max(val, 0) + 15, f"{val:.0f}µA",
                    ha="center", va="bottom", fontsize=7.5)
    ax.axhline(id_ceiling, color="gray", ls=":", lw=1,
               label=f"Limit {id_ceiling:.0f}µA")
    ax.axhline(0, color="black", lw=0.5)
    vth_idx = next(i for i, v in enumerate(vgs_steps) if v > (vth - 0.01))
    ax.axvspan(vth_idx - 0.5, len(vgs_steps) - 0.5, alpha=0.06, color="green")
    ax.text(vth_idx, id_ceiling * 1.08, "above Vth →",
            fontsize=7.5, color="green", alpha=0.8)
    ax.set_xlabel("Vgs (V)"); ax.set_ylabel("Id_sat (µA)")
    ax.set_title("Saturation current vs gate voltage")
    ax.set_ylim(-80, id_ceiling * 1.25)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(png_file, dpi=150, bbox_inches="tight")
    plt.show()
    print(f"  Saved → {png_file}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*55)
    print("  SI2302CDS — Test 1 + Test 2")
    print("="*55)
    print()
    print("  CIRCUIT:")
    print("  NI AO ch1 → 10kΩ → Drain (pin3) → AI ch0")
    print("  DAC1 CH2  → Gate  (pin1) → AI ch2")
    print("  Source (pin2) → AI ch1 → 100Ω → GND")
    print()
    print("  config.py: AO_VOLTAGE_RANGE = (0.0, 10.0) required")
    print(f"  R_drain={R_DRAIN/1000:.0f}kΩ  R_shunt={R_SHUNT:.0f}Ω")
    print()

    dac_initialize()
    ao_zero()

    try:
        vth = run_test1()
        print(f"\n  Test 1 done. "
              f"{'Vth = ' + f'{vth*1000:.1f}mV' if vth else 'Vth not extracted.'}")
        run_test2(vth)
        print("\n  All tests complete.")
    except KeyboardInterrupt:
        print("\n  Aborted by user.")
    finally:
        ao_zero()
        dac_clear_all()