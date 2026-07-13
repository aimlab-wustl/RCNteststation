# ============================================================
# test_pfi.py — PFI / Counter verification
# Mirrors MATLAB DOfast.m counter test
#
# Wiring required:
#   PFI2 ──────────────────► PFI0   (loopback for count/freq test)
#   PFI2 ──────────────────► AI0    (loopback to verify with ADC)
#
# USB-6212 pin reference:
#   PFI2  = pin 13
#   PFI0  = pin 11
#   AI0   = pin 68  (AI0+), pin 67 (AIGND)
# ============================================================

import time
import hardware as hw

PASS = "  ✓ PASS"
FAIL = "  ✗ FAIL"

print("=" * 56)
print("  PFI / COUNTER TEST — NI USB-6212 (Dev2)")
print("=" * 56)
hw.initialize()

results = []

# ── TEST 1: generate pulse, count edges ──────────────────────
print("\n[TEST 1]  ctr0 → PFI2 → PFI0  (edge count loopback)")
TARGET_FREQ = 10_000    # 10 kHz
GATE_TIME   = 0.5       # seconds

pulse_task = hw.generate_pulse(frequency=TARGET_FREQ, counter="ctr0", output_pfi_line=2)
try:
    time.sleep(0.05)
    count = hw.count_edges(duration=GATE_TIME, pfi_line=0, counter="ctr1")
finally:
    hw.stop_pulse(pulse_task)

measured_hz = count / GATE_TIME
error_pct   = abs(measured_hz - TARGET_FREQ) / TARGET_FREQ * 100
ok = error_pct < 1.0
results.append(ok)
tag = PASS if ok else FAIL
print(f"{tag}  Expected={TARGET_FREQ} Hz  Counted={count} edges  "
      f"→ {measured_hz:.1f} Hz  error={error_pct:.3f}%")

# ── TEST 2: frequency measurement mode ───────────────────────
print("\n[TEST 2]  ctr0 → PFI2 → PFI0  (hardware frequency measure)")
for target in [1_000, 10_000, 100_000]:
    pulse_task = hw.generate_pulse(frequency=target, counter="ctr0", output_pfi_line=2)
    try:
        time.sleep(0.05)
        freq = hw.measure_frequency(pfi_line=0, meas_time=0.2, counter="ctr1")
    finally:
        hw.stop_pulse(pulse_task)
    err = abs(freq - target) / target * 100
    ok  = err < 1.0
    results.append(ok)
    tag = PASS if ok else FAIL
    print(f"{tag}  Target={target:>7} Hz  Measured={freq:>10.2f} Hz  "
          f"error={err:.4f}%")

# ── TEST 3: AI triggered by PFI ──────────────────────────────
print("\n[TEST 3]  AI acquisition triggered by PFI0 rising edge")
print("          (ctr0 → PFI2 → PFI0 → AI trigger,  PFI2 → AI0 for capture)")
import nidaqmx
from nidaqmx.constants import AcquisitionType
import numpy as np
from config import DEVICE, AI_VOLTAGE_RANGE
from nidaqmx.constants import TerminalConfiguration

TRIG_FREQ   = 5_000
NUM_SAMPLES = 2_000
RATE        = 100_000

pulse_task = hw.generate_pulse(frequency=TRIG_FREQ, counter="ctr0", output_pfi_line=2)
time.sleep(0.05)

try:
    with nidaqmx.Task() as ai_task:
        ai_task.ai_channels.add_ai_voltage_chan(
            f"{DEVICE}/ai0",
            min_val=AI_VOLTAGE_RANGE[0],
            max_val=AI_VOLTAGE_RANGE[1],
            terminal_config=TerminalConfiguration.RSE,
        )
        ai_task.timing.cfg_samp_clk_timing(
            rate=RATE,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=NUM_SAMPLES,
        )
        hw.arm_ai_trigger(ai_task, pfi_line=0, edge="rising")
        ai_task.start()
        data = np.array(
            ai_task.read(number_of_samples_per_channel=NUM_SAMPLES, timeout=5.0)
        )

    signal_range = data.max() - data.min()
    ok = signal_range > 0.5       # should see a pulse waveform
    results.append(ok)
    tag = PASS if ok else FAIL
    print(f"{tag}  Triggered acquisition: {NUM_SAMPLES} samples captured  "
          f"signal range={signal_range:.3f}V")
except Exception as e:
    results.append(False)
    print(f"{FAIL}  Triggered AI failed: {e}")
finally:
    hw.stop_pulse(pulse_task)

# ── Summary ───────────────────────────────────────────────────
hw.zero_all()
passed = sum(results)
total  = len(results)
print("\n" + "=" * 56)
print(f"  RESULT:  {passed}/{total} tests passed", end="  ")
print("All good!" if passed == total else "Check wiring — PFI12→PFI0 and PFI12→AI0")
print("=" * 56)