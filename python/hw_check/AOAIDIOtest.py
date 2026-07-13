# ============================================================
# loopback_test.py — Hardware Loopback Verification
# ============================================================
# Required physical wiring before running:
#
#   AO0  ──────────────────────►  AI0    (analog loopback A)
#   AO1  ──────────────────────►  AI3    (analog loopback B)
#   Port0/Line4 (DIO out) ─────►  Port0/Line6 (DIO in)
#
# GND connections must be shared (AIGND / DGND on USB-6212).
# ============================================================

import time
import hardware as hw

PASS = "  ✓ PASS"
FAIL = "  ✗ FAIL"

def check(label: str, measured: float, expected: float, tol: float = 0.05) -> bool:
    err = abs(measured - expected)
    ok  = err <= tol
    tag = PASS if ok else FAIL
    print(f"{tag}  {label}:  expected={expected:.4f}V  measured={measured:.4f}V  err={err:.4f}V")
    return ok


# ── 1. Device init ────────────────────────────────────────────
print("=" * 56)
print("  LOOPBACK TEST — NI USB-6212 (Dev2)")
print("=" * 56)
hw.initialize()

results = []

# ── 2. AO0 → AI0 loopback ─────────────────────────────────────
print("\n[TEST 1]  AO0 → AI0  (analog loopback A)")
test_voltages = [0.0, 1.0, 2.5, 4.0, 5.0]
for v in test_voltages:
    hw.write_single(channel=0, voltage=v)
    time.sleep(0.02)
    measured = hw.read_single(channels=0)
    ok = check(f"AO0={v}V -> AI0", measured, expected=v, tol=0.08)
    results.append(ok)

# ── 3. AO1 → AI3 loopback ─────────────────────────────────────
print("\n[TEST 2]  AO1 → AI3  (analog loopback B)")
for v in test_voltages:
    hw.write_single(channel=1, voltage=v)
    time.sleep(0.02)
    measured = hw.read_single(channels=3)
    ok = check(f"AO1={v}V -> AI3", measured, expected=v, tol=0.08)
    results.append(ok)

hw.zero_all()

# ── 4. DIO Line4 (out) → Line6 (in) ──────────────────────────
# The output task is kept open for the entire loop, plus a "settle then
# majority-vote" read. The intermittency before was because
# nidaqmx.Task.write() returns when the USB packet is acknowledged
# by the host driver, not when the pin has physically transitioned.
# Windows time.sleep() granularity (~1–15ms) is comparable to USB
# latency, so 10ms is not always enough. We now:
#   1. settle 25ms after write
#   2. read 5 times and take the majority — kills any single late sample
print("\n[TEST 3]  DIO Line4 (output) -> Line6 (input)")
with hw.DIOOutputSession(4, initial_values=[False]) as out_task:
    # Warmup write — first transaction on a fresh task has more latency
    out_task.write([False])
    time.sleep(0.05)
    _ = hw.get_line(6)

    for expected_state in [True, False, True, False, True, False]:
        out_task.write([expected_state])
        time.sleep(0.025)                                # 25ms settle
        votes = [hw.get_line(6) for _ in range(5)]       # 5 reads
        measured_state = sum(votes) > 2                  # majority
        ok = (measured_state == expected_state)
        tag = PASS if ok else FAIL
        print(f"{tag}  Line4={'HIGH' if expected_state else 'LOW '} -> "
              f"Line6={'HIGH' if measured_state else 'LOW '}  votes={votes}")
        results.append(ok)
    out_task.write([False])

# ── 5. Summary ────────────────────────────────────────────────
passed = sum(results)
total  = len(results)
print("\n" + "=" * 56)
print(f"  RESULT:  {passed}/{total} tests passed", end="  ")
if passed == total:
    print("All good!")
else:
    print("Some tests failed -- check wiring or config.py ranges.")
print("=" * 56)
