"""
hardware/stm_step_capture.py
=============================
Python control for the CAPTURE_STEP firmware command.

PHYSICAL WIRING:
    PD9 (DIO9)  -> OPA4388 A+  (direct, or via 1k/50 divider for small-signal)
    OPA4388 Aout -> 10k (R1) -> PA1
                    PA1 -> 10k (R2) -> GND
    (10k/10k Aout->PA1 divider: 0.5x scaling, keeps Aout swing inside PA1's
     3.3V limit. Change DIVIDER_RATIO below if you use different values.)
    Gain-11 feedback network (Rf=100k, Rg=10k, Vref=2.5V): unchanged.

LARGE-SIGNAL vs SMALL-SIGNAL:
    Direct PD9 (3.3V step): measures overload recovery, slew rate.
    1kOhm/50Ohm divider on A+ (157mV step): keeps amp in linear region,
    gives real bandwidth estimate. Change OUT_BASE to keep runs separate.

NOTE: PD9 is assumed OUTPUT mode from MX_GPIO_Init(). If it was set to
INPUT during DIO testing, send DIO_WRITE 9 0 before running this script.
"""

import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from hardware import cdc_serial

ADCFAST_MAX_SAMPLES = 8000
VREF_ONBOARD  = 3.3     # STM32 onboard ADC reference voltage
DIVIDER_RATIO = 0.5     # Aout->PA1 divider: 10k/(10k+10k) = 0.5
                         # Aout_reconstructed = raw_PA1_V / DIVIDER_RATIO


def capture_step(n_samples: int, prescaler: int, period: int,
                 pretrig_pct: int = 20,
                 timeout_s: float = 10.0) -> dict:
    """
    Trigger a step on PD9 and capture the response on PA1.
    pretrig_pct% of samples are captured BEFORE the step fires,
    giving a flat baseline that makes the edge clearly visible.
    t=0 in the returned time axis is the step edge.

    Returns dict:
        raw_V      -- PA1 voltage array (before divider correction)
        aout_V     -- reconstructed Aout array (after divider)
        t          -- time axis in seconds, t=0 = step edge
        n          -- number of samples
        rate_hz    -- assumed sample rate (from prescaler/period)
        dt         -- sample period in seconds
        pretrig_n  -- number of pre-step samples
        round_trip_s
    """
    if n_samples > ADCFAST_MAX_SAMPLES:
        raise ValueError(f"n_samples max is {ADCFAST_MAX_SAMPLES}")

    port = cdc_serial.open_port()
    cmd = f"CAPTURE_STEP {n_samples} {prescaler} {period} {pretrig_pct}"

    t0 = time.time()
    port.reset_input_buffer()
    port.write((cmd.strip() + "\n").encode("ascii"))
    port.flush()

    # Protocol: optional PRETRIG line, then BINARY:<n_bytes>, then
    # <binary payload>, then OK:CAPTURE_STEP_DONE
    pretrig_n = 0
    header = port.readline().decode("ascii", errors="replace").strip()
    if header.startswith("ERR:"):
        raise RuntimeError(f"CAPTURE_STEP failed: {header}")
    if header.startswith("PRETRIG:"):
        pretrig_n = int(header[len("PRETRIG:"):])
        header = port.readline().decode("ascii", errors="replace").strip()
    if not header.startswith("BINARY:"):
        raise RuntimeError(f"unexpected response (expected BINARY:...): {header!r}")
    n_bytes = int(header[len("BINARY:"):])

    payload = port.read(n_bytes)
    if len(payload) != n_bytes:
        raise RuntimeError(f"expected {n_bytes} bytes, got {len(payload)}")

    ok_line = port.readline().decode("ascii", errors="replace").strip()
    if not ok_line.startswith("OK:"):
        raise RuntimeError(f"expected OK: after payload, got {ok_line!r}")

    round_trip_s = time.time() - t0

    raw_codes = np.frombuffer(payload, dtype="<u2").astype(np.float64)
    raw_V  = raw_codes / 65535.0 * VREF_ONBOARD
    aout_V = raw_V / DIVIDER_RATIO
    rate_hz = 240e6 / (prescaler + 1) / (period + 1)
    dt = 1.0 / rate_hz
    t  = (np.arange(len(raw_V)) - pretrig_n) * dt

    return {
        "raw_V":  raw_V, "aout_V": aout_V, "t": t,
        "n": len(raw_V), "rate_hz": rate_hz, "dt": dt,
        "pretrig_n": pretrig_n, "round_trip_s": round_trip_s,
    }


def analyse_step(result: dict, settle_pct: float = 1.0) -> dict:
    """
    Extract step-response metrics. Works for both rising and falling
    steps -- detects direction automatically from the data.

    settle_pct: settling band as % of step size (default 1%).
    For noisy captures, try 2.0 to avoid noise crossings dominating.

    NOTE: bandwidth_est_Hz is only valid for small-signal steps where
    the op-amp stays in its linear region. For large GPIO steps
    (direct PD9, no divider) it significantly underestimates true BW
    because slew limiting and saturation recovery dominate rise time.
    """
    v      = result["aout_V"]
    dt     = result["dt"]
    pretrig_n = result.get("pretrig_n", 0)

    # Baseline from pre-trigger region
    pre_n     = max(1, pretrig_n)
    v_initial = float(np.median(v[:pre_n]))

    # Final settled value: median of last 20% -- median is robust
    # against noise outliers that bias mean-based estimates and cause
    # the settling band to never be satisfied (settling=nan)
    v_final   = float(np.median(v[int(0.8 * len(v)):]))
    step_size = v_final - v_initial
    rising    = step_size > 0

    if abs(step_size) < 0.01:
        return {
            "error": "step size too small (<10mV) -- check wiring and PD9 state",
            "v_initial": v_initial, "v_final": v_final, "step_size_V": step_size,
        }

    # Slew rate: max |dV/dt| in the first 200 post-step samples (V/us)
    dv   = np.diff(v) / dt
    post = slice(pretrig_n, min(len(dv), pretrig_n + 200))
    slew_rate_V_us = float(np.max(np.abs(dv[post])) * 1e-6)

    # 10->90% rise/fall time
    v10 = v_initial + 0.10 * step_size
    v90 = v_initial + 0.90 * step_size
    if rising:
        t10_idx = next((i for i in range(pretrig_n, len(v)) if v[i] >= v10), None)
        t90_idx = next((i for i in range(pretrig_n, len(v)) if v[i] >= v90), None)
    else:
        t10_idx = next((i for i in range(pretrig_n, len(v)) if v[i] <= v10), None)
        t90_idx = next((i for i in range(pretrig_n, len(v)) if v[i] <= v90), None)

    rise_time_is_upper_bound = False
    if t10_idx is not None and t90_idx is not None:
        rise_time_us = float((t90_idx - t10_idx) * dt * 1e6)
        if rise_time_us == 0.0:
            rise_time_us = dt * 1e6   # faster than one sample: report upper bound
            rise_time_is_upper_bound = True
    else:
        rise_time_us = float("nan")

    bw_est_Hz = (0.35 / (rise_time_us * 1e-6)
                 if not np.isnan(rise_time_us) else float("nan"))

    # Overshoot
    if rising:
        peak_v = float(np.max(v[pretrig_n:]))
        overshoot_pct = max(0.0, (peak_v - v_final) / abs(step_size) * 100)
    else:
        peak_v = float(np.min(v[pretrig_n:]))
        overshoot_pct = max(0.0, (v_final - peak_v) / abs(step_size) * 100)

    # Settling time: sliding-window approach -- find the first point
    # where >= WIN_FRAC of the next WINDOW samples are inside the band.
    # This tolerates occasional noise spikes without requiring a perfect
    # run of consecutive clean samples (which rarely happens at 3.2MSPS
    # noise levels), and avoids the "always reports end of window" failure
    # mode of the previous backward-scan approach.
    band     = abs(step_size) * settle_pct / 100.0
    inside   = (np.abs(v[pretrig_n:] - v_final) <= band).astype(np.float32)
    WINDOW   = 32     # samples; at 3.2MSPS = ~10us per window
    WIN_FRAC = 0.80   # 80% of window must be inside band

    if len(inside) < WINDOW:
        settling_us = float("nan")
    else:
        cs      = np.concatenate([[0.0], np.cumsum(inside)])
        win_sum = cs[WINDOW:] - cs[:-WINDOW]
        good    = np.where(win_sum >= WIN_FRAC * WINDOW)[0]
        settling_us = float(good[0] * dt * 1e6) if len(good) > 0 else float("nan")

    return {
        "rise_time_us":             rise_time_us,
        "rise_time_is_upper_bound": rise_time_is_upper_bound,
        "slew_rate_V_us":           slew_rate_V_us,
        "overshoot_pct":            overshoot_pct,
        "settling_us":              settling_us,
        "bandwidth_est_Hz":         bw_est_Hz,
        "v_initial":                v_initial,
        "v_final":                  v_final,
        "step_size_V":              step_size,
        "settle_pct_used":          settle_pct,
        "WARNING": ("bandwidth_est_Hz underestimated for large-signal steps "
                    "-- use small-signal divider (1k/50) for true BW"),
    }


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from scipy.io import savemat

    OUT_BASE    = "step_response_test"   # prefix for all saved files
    SETTLE_PCT  = 2.0               # wider band reduces noise-crossing artifacts

    print("Running step-response capture at ~3.2MSPS, 20% pre-trigger...")
    # Force PD9 LOW and wait for Aout to fully settle before arming
    # the capture -- prevents the previous run's step edge from
    # appearing as a spike in the pre-trigger baseline window
    cdc_serial.open_port()
    cdc_serial.send_command("DIO_WRITE 9 0")
    time.sleep(0.1)   # 100ms -- plenty for any prior transient to settle

    r = capture_step(8000, prescaler=0, period=74, pretrig_pct=20)
    print(f"  n={r['n']}  rate={r['rate_hz']/1e6:.3f}MHz  "
          f"pretrig={r['pretrig_n']} samples  "
          f"round_trip={r['round_trip_s']*1000:.1f}ms")
    print(f"  Aout: min={r['aout_V'].min():.4f}V  max={r['aout_V'].max():.4f}V  "
          f"pre-step mean={r['aout_V'][:r['pretrig_n']].mean():.4f}V")

    m = analyse_step(r, settle_pct=SETTLE_PCT)

    if "error" in m:
        print(f"\n  Analysis error: {m['error']}")
        print("  Check: is PD9 in OUTPUT mode? Does Aout actually change?")
    else:
        rise_note = " (<1 sample, upper bound)" if m["rise_time_is_upper_bound"] else ""
        print(f"\nStep-response metrics (Aout, reconstructed via 10k/10k divider):")
        print(f"  Step direction: {'rising' if m['step_size_V']>0 else 'falling'}")
        print(f"  Step size:      {m['step_size_V']:.4f}V  "
              f"({m['v_initial']:.4f}V -> {m['v_final']:.4f}V)")
        print(f"  Slew rate:      {m['slew_rate_V_us']:.3f} V/us  "
              f"(datasheet OPA4388: 5 V/us)")
        print(f"  10-90% time:    {m['rise_time_us']:.3f} us{rise_note}")
        print(f"  Overshoot:      {m['overshoot_pct']:.2f}%")
        print(f"  Settling ({SETTLE_PCT:.0f}%): {m['settling_us']:.2f} us")
        print(f"  BW estimate:    {m['bandwidth_est_Hz']/1e3:.1f} kHz")
        print(f"  NOTE: {m['WARNING']}")

    # ── Save data ──────────────────────────────────────────────────────
    np.savez(OUT_BASE + ".npz",
             t=r["t"], aout_V=r["aout_V"], raw_V=r["raw_V"],
             rate_hz=r["rate_hz"], pretrig_n=r["pretrig_n"])

    try:
        savemat(OUT_BASE + ".mat", {
            "t":         r["t"],
            "aout_V":    r["aout_V"],
            "raw_V":     r["raw_V"],
            "rate_hz":   r["rate_hz"],
            "pretrig_n": float(r["pretrig_n"]),
        })
        print(f"\n  saved {OUT_BASE}.mat  (MATLAB: d=load(..); plot(d.t*1e6,d.aout_V))")
    except ImportError:
        print("  scipy not found -- .mat skipped (pip install scipy)")

    metrics_out = {k: (float(v) if isinstance(v, (int, float, np.floating))
                       else bool(v) if isinstance(v, (bool, np.bool_))
                       else str(v))
                   for k, v in m.items()}
    metrics_out.update({"rate_hz": float(r["rate_hz"]),
                        "pretrig_n": int(r["pretrig_n"]),
                        "n_samples": int(r["n"])})
    with open(OUT_BASE + "_metrics.json", "w") as f:
        json.dump(metrics_out, f, indent=2)

    print(f"  saved {OUT_BASE}.npz / .mat / _metrics.json")

    # ── Plot ───────────────────────────────────────────────────────────
    t_us = r["t"] * 1e6

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))

    ax1.plot(t_us, r["aout_V"], linewidth=0.6)
    ax1.axvline(0, color="r", ls="--", lw=0.8, label="step edge")
    ax1.set_xlabel("Time (us, t=0=step)")
    ax1.set_ylabel("Aout (V)")
    ax1.set_title("Full capture (pre-trigger + settling)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    mask = (t_us >= -10) & (t_us <= 100)
    ax2.plot(t_us[mask], r["aout_V"][mask], lw=0.8, marker=".", ms=2)
    ax2.axvline(0, color="r", ls="--", lw=0.8)
    if "error" not in m:
        ax2.set_title(
            f"Zoomed -10..+100us | "
            f"slew={m['slew_rate_V_us']:.2f}V/us  "
            f"settling({SETTLE_PCT:.0f}%)={m['settling_us']:.1f}us"
        )
    else:
        ax2.set_title("Zoomed -10..+100us")
    ax2.set_xlabel("Time (us, t=0=step)")
    ax2.set_ylabel("Aout (V)")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT_BASE + ".png", dpi=150)
    print(f"  saved {OUT_BASE}.png")
    plt.show()