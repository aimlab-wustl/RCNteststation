"""
stm_adctest.py
===============
Full validation sequence for the ADC1/PA1 fast-capture path.

  1. STATUS baseline, before touching anything.
  2. Step through increasing rates: 10kSPS (proven baseline) ->
     100kSPS -> 1MSPS -> the ~3.2MSPS assumed ceiling. At each step:
     run a capture, then check ADCFAST_DBG's elapsed_ms (measured via
     HAL_GetTick(), not computed) and adc_errors (DMA/ADC overrun --
     only a real risk near the ceiling).
  3. STATUS again at the end -- confirms ADC1 restored cleanly.

CAVEAT worth knowing before reading the results: HAL_GetTick() only
has 1ms resolution. At 10kSPS/1000 samples the expected window is
100ms, so elapsed_ms is meaningfully precise (~1% resolution). At
1MSPS/8000 samples the window is only ~8ms (~12% resolution), and at
the ~3.2MSPS ceiling it's ~2.5ms (order-of-magnitude only). This
script accounts for that -- it applies a tight check at low rates and
only a "way off" sanity check at high rates, rather than expecting
tick-level precision where the tick itself is too coarse to give it.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware import cdc_serial
from hardware.stm_adc_fast import capture, capture_at_rate, ADCFAST_MAX_SAMPLES


def _parse_dbg(resp: str) -> dict:
    payload = resp[len("DATA:"):] if resp.startswith("DATA:") else resp
    out = {}
    for kv in payload.strip().split():
        k, _, v = kv.partition("=")
        if k:
            out[k] = int(v) if v.lstrip("-").isdigit() else v
    return out


def check_dbg(label: str, expected_ms: float) -> bool:
    resp = cdc_serial.send_command("ADCFAST_DBG")
    print(f"  {resp}")
    fields = _parse_dbg(resp)
    elapsed = fields.get("elapsed_ms", -1)
    errors = fields.get("adc_errors", -1)
    ok = True

    if errors != 0:
        print(f"    WARNING [{label}]: adc_errors={errors} -- DMA/ADC "
              f"overrun detected, likely at/above the real rate ceiling")
        ok = False

    if expected_ms < 5:
        # HAL_GetTick()'s 1ms resolution can't precisely verify sub-5ms
        # windows -- only flag if elapsed is WAY beyond what tick noise
        # alone could explain.
        if elapsed > expected_ms * 10 + 5:
            print(f"    WARNING [{label}]: elapsed_ms={elapsed} is far "
                  f"beyond expected ~{expected_ms:.2f}ms even accounting "
                  f"for 1ms tick resolution")
            ok = False
        else:
            print(f"    [{label}] elapsed_ms={elapsed} (expected "
                  f"~{expected_ms:.2f}ms -- tick resolution too coarse "
                  f"for a precise check at this rate; order-of-magnitude "
                  f"only)")
    else:
        if abs(elapsed - expected_ms) > max(2, expected_ms * 0.2):
            print(f"    WARNING [{label}]: elapsed_ms={elapsed} vs "
                  f"expected ~{expected_ms:.1f} -- rate may not be what's "
                  f"assumed")
            ok = False
        else:
            print(f"    [{label}] elapsed_ms={elapsed} matches expected "
                  f"~{expected_ms:.1f} -- rate confirmed")

    return ok


cdc_serial.open_port()
all_ok = True

print("=== STATUS before ===")
print(cdc_serial.send_command("STATUS"))

# Step 1: proven baseline, unchanged from earlier validation
print("\n=== 10 kSPS baseline (1000 samples) ===")
r = capture_at_rate(1000, 10_000)
expected_ms = 1000 / r["rate_hz"] * 1000
print(f"  round_trip={r['round_trip_s']*1000:.1f}ms  "
      f"raw min/max/mean/std = {r['raw'].min()}/{r['raw'].max()}/"
      f"{r['raw'].mean():.1f}/{r['raw'].std():.1f}")
all_ok &= check_dbg("10kSPS", expected_ms)

# Steps 2-3: push up incrementally, max samples for the best possible
# elapsed_ms resolution at each rate
for label, rate in [("100 kSPS", 100_000), ("1 MSPS", 1_000_000)]:
    print(f"\n=== {label} ({ADCFAST_MAX_SAMPLES} samples) ===")
    r = capture_at_rate(ADCFAST_MAX_SAMPLES, rate)
    expected_ms = ADCFAST_MAX_SAMPLES / r["rate_hz"] * 1000
    print(f"  round_trip={r['round_trip_s']*1000:.1f}ms  "
          f"raw min/max/mean/std = {r['raw'].min()}/{r['raw'].max()}/"
          f"{r['raw'].mean():.1f}/{r['raw'].std():.1f}")
    all_ok &= check_dbg(label, expected_ms)

# Step 4: the assumed ~3.2MSPS ceiling -- explicit prescaler/period
# (documented in adc_capture.h) rather than capture_at_rate's rounding
print(f"\n=== ~3.2 MSPS ceiling ({ADCFAST_MAX_SAMPLES} samples, "
      f"prescaler=0 period=74) ===")
r = capture(ADCFAST_MAX_SAMPLES, prescaler=0, period=74)
expected_ms = ADCFAST_MAX_SAMPLES / r["rate_hz"] * 1000
print(f"  rate={r['rate_hz']/1e6:.3f}MHz (assumed)  "
      f"round_trip={r['round_trip_s']*1000:.1f}ms  "
      f"raw min/max/mean/std = {r['raw'].min()}/{r['raw'].max()}/"
      f"{r['raw'].mean():.1f}/{r['raw'].std():.1f}")
all_ok &= check_dbg("~3.2MSPS ceiling", expected_ms)

print("\n=== STATUS after ===")
print(cdc_serial.send_command("STATUS"))

print("\n" + ("ALL CHECKS PASSED" if all_ok else
              "SOME CHECKS FAILED OR FLAGGED -- see WARNINGs above"))