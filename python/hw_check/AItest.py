# ============================================================
# test_continuous.py — Quick test for read_continuous()
# Wiring: connect AO0 to AI0 (same loopback wire from before)
# ============================================================

import hardware as hw

hw.initialize()

# Output a steady 2.5V on AO0 so the oscilloscope has something to show
hw.write_single(channel=0, voltage=2.5)
print("[test] AO0 set to 2.5V — you should see a flat line at 2.5V")
print("[test] Try connecting a signal generator to AI0 for something interesting")
print("[test] Close the plot window or press STOP to end.\n")

# Run continuous acquisition — window closes when you hit STOP or close the plot
v, t = hw.read_continuous(
    channel     = 0,
    rate        = 10_000,       # 10 kS/s — good for most signals, easy on CPU
    window_sec  = 1.0,          # show last 1 second on screen
    chunk_sec   = 0.05,         # callback every 50ms — responsive scrolling
    csv_filename= "continuous_test.csv",
)

hw.zero_all()

print(f"\n[test] Captured {len(v)} samples over {t[-1]:.2f}s")
print(f"[test] Min={v.min():.4f}V  Max={v.max():.4f}V  Mean={v.mean():.4f}V")
print("[test] Data saved to continuous_test.csv")