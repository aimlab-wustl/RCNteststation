# from hardware.ads131a04 import ADS131

# adc = ADS131()

# # ── Calibration ──────────────────────────────────────────────
# # adc.calibrate()       # run ONCE with AINxP shorted to AINxN, saves cal_ads131.json
# adc.load_cal()          # run every session to apply saved offsets

# # ── Health check ─────────────────────────────────────────────
# adc.selftest()          # both chips: registers + all 8 channel readings

# # ── Single reads ─────────────────────────────────────────────
# v = adc.read_single(1, 1)             # chip1 CH1 → float volts
# v = adc.read_single(2, 3)             # chip2 CH3

# frame = adc.read_frame(1)             # chip1 all 4ch → {1:V, 2:V, 3:V, 4:V}
# data  = adc.read_all()               # both chips all 8ch → {'C1CH1':V, ..., 'C2CH4':V}

# # ── Data rate (OSR) ──────────────────────────────────────────
# # fMOD = 2MHz on your hardware. OSR trades speed for noise:
# #   set_osr(chip, 4096) →  0.5 kSPS   lowest noise
# #   set_osr(chip, 2048) →  1.0 kSPS
# #   set_osr(chip, 1024) →  2.0 kSPS
# #   set_osr(chip, 512)  →  4.0 kSPS
# #   set_osr(chip, 400)  →  5.0 kSPS  ← default (good for DC)
# #   set_osr(chip, 256)  →  8.0 kSPS
# #   set_osr(chip, 128)  → 16.0 kSPS
# #   set_osr(chip, 64)   → 32.0 kSPS
# #   set_osr(chip, 32)   → 62.5 kSPS  highest speed, most noise
# adc.set_osr(1, 32)     # apply to chip 1
# adc.set_osr(2, 32)     # apply to chip 2

# # ── Buffered capture — finite block, ASCII path (~5kSPS) ─────
# # Good for precision DC measurements and statistics.
# v, t = adc.read_buffered(chip=1, num_frames=1000)
# # v: numpy array shape (4, N) — v[0]=CH1, v[1]=CH2, v[2]=CH3, v[3]=CH4
# # t: numpy array of timestamps in seconds
# print(f"CH1: mean={v[0].mean():.6f}V  std={v[0].std()*1e6:.1f}µV")
# print(f"CH2: mean={v[1].mean():.6f}V  std={v[1].std()*1e6:.1f}µV")

# # ── DMA streaming — live plot, high speed ────────────────────
# # Blocks until window closed or duration reached.
# # v shape: (4, N) — all 4 channels captured simultaneously.

# # 5kSPS, 10 seconds, display CH1
# adc.set_osr(1, 400)
# v, t = adc.read_dma(chip=1, duration=10, display_ch=1)

# # 62.5kSPS, 10 seconds
# adc.set_osr(1, 32)
# v, t = adc.read_dma(chip=1, duration=10, display_ch=1)

# # Wider time window on plot
# v, t = adc.read_dma(chip=1, duration=10, display_ch=1, window_sec=5.0)

# # Indefinite — close window or press STOP to end
# # v, t = adc.read_dma(chip=1, display_ch=1)

# # ── Save to CSV ──────────────────────────────────────────────
# # Buffered → CSV via numpy
# import numpy as np
# adc.set_osr(1, 400)
# v, t = adc.read_buffered(chip=1, num_frames=5000)
# np.savetxt("capture_buffered.csv",
#            np.column_stack([t, v[0], v[1], v[2], v[3]]),
#            delimiter=",",
#            header="Time_s,CH1_V,CH2_V,CH3_V,CH4_V",
#            comments="", fmt="%.8f")
# print("Saved capture_buffered.csv")

# # DMA → CSV built-in
# adc.set_osr(1, 32)
# v, t = adc.read_dma(chip=1, duration=5, display_ch=1,
#                     csv_filename="capture_dma.csv")
# print("Saved capture_dma.csv")

# # ── Chip 2 ───────────────────────────────────────────────────
# adc.set_osr(2, 400)
# v2, t2 = adc.read_buffered(chip=2, num_frames=500)
# print(f"Chip2 CH1: mean={v2[0].mean():.6f}V")

# v2, t2 = adc.read_dma(chip=2, duration=10, display_ch=1)



# # from hardware.ads131a04 import ADS131
# # adc = ADS131()
# # # adc.calibrate()
# # adc.load_cal()
# # adc.selftest()

# # # Single reads
# # print(adc.read_single(1, 1))      # chip1 ch1
# # print(adc.read_frame(1))          # all 4 ch of chip1
# # print(adc.read_all())             # all 8 channels
# # adc.set_osr(1, 32)

# # # Buffered capture
# # v, t = adc.read_buffered(1, 500)  # 500 frames from chip1
# # print(f"Rate: {len(t)/t[-1]:.0f} SPS")
# # print(f"CH1 mean: {v[0].mean():.6f}V")

# # # Live plot
# # adc.read_continuous(1, 1)         # chip1, ch1, live oscilloscope

# # # from hardware.cdc_serial import open_port, send_command
# # # import time
# # # p = open_port()

# # # print(send_command("ADS_DBG", port=p))          # before stream
# # # send_command("ADS_DMA_STREAM 1 0", port=p)
# # # time.sleep(0.1)                                  # just 100ms
# # # send_command("ADS_DMA_STOP", port=p)
# # # print(send_command("ADS_DBG", port=p))          # after

# # # from hardware.ads131a04 import ADS131
# # # adc = ADS131()
# # # adc.selftest()
# # # adc.dma_diagnostic(1)

# # # v, t = adc.read_dma(chip=1, duration=10, display_ch=1)
# # # print(f"Rate: {len(t)/t[-1]:.0f} SPS")

# # # adc.set_osr(1, 32)   # 62.5kSPS hardware rate
# # # v, t = adc.read_dma(chip=1, duration=10, display_ch=1)
# # # print(f"Rate: {len(t)/t[-1]:.0f} SPS")

"""
ads131_record_2min.py
=======================
Headless (no live plot) continuous recording at full ADS131A04 speed,
for a fixed duration -- CHIP 1 / CHANNEL 1 ONLY.

Reuses the same proven binary packet parsing as ADS131.read_dma(),
with two changes from the first version:
  1. Fixed a real progress-print bug: the original condition
     (elapsed % 10 == 0) stayed True for the WHOLE second whenever
     elapsed's integer part was divisible by 10, firing the print on
     every loop iteration during that entire second (thousands of
     times, just hidden by \r overwriting) instead of once. Fixed by
     tracking the last-printed second explicitly.
  2. Only decodes/stores channel 1 -- the wire format still sends all
     4 channels per frame (can't change that, it's the SPI frame
     shape), but skipping the sign-extension math and list-append for
     channels 2-4 cuts per-frame Python work ~4x, which matters for
     keeping up with the incoming rate over a full 2-minute capture.

BANDWIDTH NOTE:
    OSR_32 (62.5kSPS) -> 15 bytes/frame x 62500/s = ~938 KB/s
    Your USB link's realistic sustained ceiling is around ~1MB/s.
    OSR_32 for a full 2 minutes sits close to that -- real (if
    small) risk of gaps if anything hiccups. OSR_64 (32kSPS,
    ~480KB/s) is meaningfully safer if you want a guaranteed
    gap-free recording instead of the absolute fastest rate.
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from hardware.ads131a04 import ADS131, VREF
from hardware.cdc_serial import send_command
 
CHIP = 1
CH = 1            # channel of interest -- only this one is decoded/stored
OSR = 256          # 62.5kSPS. Use 64 (32kSPS) for more USB headroom.
DURATION_S = 10
OUT_FILE = "ads131_10s_ch1_precise.npz"

FRAME_BYTES = 15
PKT_HEADER = 6
FRAMES_PER_PKT = 32


def _parse_ch1(raw15: bytes) -> float:
    """Decode ONLY channe 1's 24-bit word from a 15-byte frame --
    skips the sign-extension/division work for channels 2-4 entirely."""
    b = raw15[3:6]   # channel 1's 3 bytes (status is raw15[0:3])
    raw24 = (b[0] << 16) | (b[1] << 8) | b[2]
    if raw24 & 0x800000:
        raw24 |= 0xFF000000
        signed = raw24 - 0x100000000
    else:
        signed = raw24
    return (signed / 8388608.0) * VREF


adc = ADS131()
adc.load_cal()
adc.set_osr(CHIP, OSR)

print(f"[record] chip={CHIP} ch={CH}  OSR={OSR}  duration={DURATION_S}s  "
      f"no live plot -- headless")

all_v = []
all_t = []
t_start = None
warmup = 0
buf = bytearray()
last_print_sec = -1   # fixed: track last-printed second explicitly

resp = send_command(f"ADS_DMA_STREAM {CHIP} 0", port=adc._port)
if resp.startswith("ERR:"):
    raise RuntimeError(f"failed to start stream: {resp}")

t0 = time.time()
try:
    while time.time() - t0 < DURATION_S:
        chunk = adc._port.read(adc._port.in_waiting or 1)
        if not chunk:
            continue
        buf.extend(chunk)

        while len(buf) >= PKT_HEADER + FRAME_BYTES:
            if buf[0] != ord('D'):
                buf = buf[1:]
                continue

            min_pkt = PKT_HEADER + FRAME_BYTES
            next_pkt = -1
            for scan in range(min_pkt, len(buf)):
                b = buf[scan]
                if b in (ord('D'), ord('O'), ord('E')):
                    if (scan - PKT_HEADER) % FRAME_BYTES == 0:
                        next_pkt = scan
                        break
            if next_pkt == -1:
                if len(buf) < PKT_HEADER + FRAMES_PER_PKT * FRAME_BYTES + 10:
                    break
                next_pkt = PKT_HEADER + min(
                    FRAMES_PER_PKT, (len(buf) - PKT_HEADER) // FRAME_BYTES
                ) * FRAME_BYTES

            n_frames = (next_pkt - PKT_HEADER) // FRAME_BYTES
            now = time.time()
            if t_start is None:
                t_start = now

            for i in range(n_frames):
                start = PKT_HEADER + i * FRAME_BYTES
                v = _parse_ch1(bytes(buf[start:start + FRAME_BYTES]))
                v = adc._apply_offset(CHIP, CH, v)
                if warmup < 4:
                    warmup += 1
                    continue
                all_v.append(v)
                all_t.append(now - t_start)

            buf = buf[next_pkt:]

        # fixed: only fires once per 10s boundary, not continuously
        elapsed = time.time() - t0
        sec = int(elapsed)
        if sec % 10 == 0 and sec != last_print_sec:
            last_print_sec = sec
            rate = len(all_t) / all_t[-1] if all_t and all_t[-1] > 0 else 0
            print(f"  {elapsed:.0f}s / {DURATION_S}s  n={len(all_t)}  "
                  f"rate={rate:.0f}SPS")

finally:
    try:
        send_command("ADS_DMA_STOP", port=adc._port)
    except Exception:
        pass

v_final = np.array(all_v, dtype=np.float64)
t_final = np.array(all_t, dtype=np.float64)

if len(t_final) > 1:
    rate = len(t_final) / t_final[-1]
    print(f"[record] Done: {len(t_final)} samples @ {rate:.0f} SPS")
    print(f"  CH{CH}: min={v_final.min():.4f}V  max={v_final.max():.4f}V  "
          f"mean={v_final.mean():.6f}V")
else:
    print("[record] WARNING: got little or no data -- check connection")

np.savez(OUT_FILE, voltage=v_final, times=t_final, osr=OSR, chip=CHIP, ch=CH)
print(f"[record] Saved -> {OUT_FILE}")


"""
ads131_view_recording.py
==========================
View a chip1/ch1 recording saved by ads131_record_2min.py, after the
fact -- no live plotting during capture, just a plot once you're
ready to look.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt

FILE = sys.argv[1] if len(sys.argv) > 1 else "ads131_10s_ch1_precise.npz"

data = np.load(FILE)
v, t = data["voltage"], data["times"]
ch, chip, osr = int(data["ch"]), int(data["chip"]), int(data["osr"])
print(f"Loaded {FILE}: {len(v)} samples, chip={chip} ch={ch} OSR={osr}, "
      f"duration={t[-1]:.1f}s")

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(t, v, linewidth=0.5)
ax.set_xlabel("Time (s)")
ax.set_ylabel(f"CH{ch} (V)")
ax.set_title(f"Chip{chip} CH{ch}: min={v.min():.4f}V max={v.max():.4f}V "
             f"mean={v.mean():.6f}V")
ax.grid(True, alpha=0.3)
fig.tight_layout()
plt.show()