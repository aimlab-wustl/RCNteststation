# ============================================================
# hardware/ads131a04.py — ADS131A04 24-bit ADC Python Driver
# AIMLAB_TESTSTATION_V3
#
# Communicates with the STM32 ADS131A04 firmware driver
# over USB CDC (COM4). Each chip has 4 differential channels,
# ±2.442V range at gain=1 (internal reference).
#
# API:
#   ADS131 class — OOP interface
#   read_single(chip, ch)         → float voltage
#   read_frame(chip)              → dict {1:V, 2:V, 3:V, 4:V}
#   read_all()                    → dict {C1CH1:V, ..., C2CH4:V}
#   read_buffered(chip, n)        → (np.ndarray voltages[4,n], times)
#   read_continuous(chip, ch)     → live plot
#   set_osr(chip, osr)            → change data rate
#   status(chip)                  → chip health dict
#
# Data rates at fMOD=2MHz (your config):
#   OSR 4096 →  0.5 kSPS    OSR 256  →  8.0 kSPS
#   OSR 2048 →  1.0 kSPS    OSR 128  → 16.0 kSPS
#   OSR 1024 →  2.0 kSPS    OSR 64   → 32.0 kSPS
#   OSR 512  →  4.0 kSPS    OSR 32   → 62.5 kSPS
#   OSR 400  →  5.0 kSPS  ← default (good starting point)
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import threading
import numpy as np

from hardware.cdc_serial import open_port, send_command, ping
from config import STM_COM_PORT, STM_BAUD_RATE, STM_TIMEOUT

# Valid OSR values and their data rates at fMOD=2MHz
OSR_RATES = {
    4096: 0.5e3,
    2048: 1.0e3,
    1024: 2.0e3,
    512:  4.0e3,
    400:  5.0e3,
    256:  8.0e3,
    128: 16.0e3,
    64:  32.0e3,
    32:  62.5e3,
}

VREF = 4.0   # 4V internal reference (VREF_4V=1, AVDD=5V AVSS=GND)


class ADS131:
    """
    ADS131A04 24-bit precision ADC interface over USB CDC.

    Two chips, 4 differential channels each, ±2.442V range.
    Chip 1: channels C1CH1–C1CH4
    Chip 2: channels C2CH1–C2CH4
    """

    CHIPS    = [1, 2]
    CHANNELS = [1, 2, 3, 4]

    def __init__(self,
                 port: str   = STM_COM_PORT,
                 baud: int   = STM_BAUD_RATE,
                 timeout: float = STM_TIMEOUT):
        self._port = open_port(port, baud, timeout)
        if not ping(self._port):
            raise RuntimeError(f"STM32 not responding on {port}")
        # Software offset correction — populated by calibrate() or load_cal()
        # offsets[chip][ch] = offset in volts to subtract from each reading
        self._offsets = {
            1: {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
            2: {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
        }
        print(f"[ADS131] Connected on {port}")

    def _apply_offset(self, chip: int, ch: int, v: float) -> float:
        """Subtract stored offset correction from a voltage reading."""
        return v - self._offsets[chip][ch]

    # ── calibrate ────────────────────────────────────────────
    def calibrate(self, chips: list = None, cal_file: str = "cal_ads131.json"):
        """
        Run offset calibration. Inputs must be shorted (AINxP to AINxN).

        Sends ADS_CAL command to firmware which averages 500 frames per
        chip. Stores offsets internally and saves to JSON file.

        Args:
            chips:    [1], [2], or [1,2] (default both)
            cal_file: path to save calibration JSON

        Example:
            adc.calibrate()                    # both chips
            adc.calibrate(chips=[1])           # chip 1 only
            adc.calibrate(cal_file="my.json")  # custom path
        """
        import json, time as _time
        if chips is None:
            chips = [1, 2]

        print("[ADS131] Starting offset calibration...")
        print("[ADS131] Ensure AINxP is shorted to AINxN on all channels.")
        input("[ADS131] Press ENTER to begin... ")

        cal_data = {"vref": VREF, "timestamp": _time.strftime("%Y-%m-%d %H:%M:%S")}

        for chip in chips:
            print(f"[ADS131] Calibrating chip {chip} (500 frames)...")
            resp = send_command(f"ADS_CAL {chip}", port=self._port)
            if resp.startswith("ERR:"):
                print(f"[ADS131] Chip {chip} calibration failed: {resp}")
                continue

            # Parse OK:ADS_CAL chip=1 CH1=120,CH2=-80,CH3=20,CH4=-20 n=500
            # Replace commas with spaces first so all tokens split uniformly
            offsets_v = {}
            flat = resp.replace(',', ' ')
            for part in flat.split():
                if part.startswith("CH") and '=' in part:
                    key, val = part.split('=', 1)
                    try:
                        ch = int(key[2:])
                        offsets_v[ch] = int(val) / 10000.0
                    except ValueError:
                        continue

            cal_data[f"chip{chip}"] = {}
            print(f"[ADS131] Chip {chip} offsets:")
            for ch in [1, 2, 3, 4]:
                v = offsets_v.get(ch, 0.0)
                self._offsets[chip][ch] = v
                cal_data[f"chip{chip}"][f"ch{ch}"] = v
                print(f"  CH{ch}: {v*1000:+.4f} mV")

        # Save to file
        with open(cal_file, "w") as f:
            import json
            json.dump(cal_data, f, indent=2)
        print(f"[ADS131] Calibration saved → {cal_file}")
        print("[ADS131] Offsets will be applied to all subsequent reads.")
        print("[ADS131] NOTE: Remove shorts from inputs before measuring signals.")

    def load_cal(self, cal_file: str = "cal_ads131.json"):
        """
        Load previously saved calibration from JSON file.
        Call this at the start of each session instead of re-calibrating.

        Example:
            adc = ADS131()
            adc.load_cal()           # load default cal_ads131.json
            v = adc.read_single(1,1) # already offset-corrected
        """
        import json
        with open(cal_file, "r") as f:
            cal_data = json.load(f)
        for chip in [1, 2]:
            key = f"chip{chip}"
            if key in cal_data:
                for ch in [1, 2, 3, 4]:
                    self._offsets[chip][ch] = cal_data[key].get(f"ch{ch}", 0.0)
        print(f"[ADS131] Calibration loaded from {cal_file}")

    def clear_cal(self):
        """Remove all offset corrections (set all offsets to 0)."""
        for chip in [1, 2]:
            for ch in [1, 2, 3, 4]:
                self._offsets[chip][ch] = 0.0
        print("[ADS131] Calibration offsets cleared.")
    @staticmethod
    def _parse_response(resp: str) -> dict:
        """
        Parse 'DATA:C1CH1=12345,C1CH2=-500,...' into
        {'C1CH1': 1.2345, 'C1CH2': -0.0500, ...}

        Values are integer ×10000 in firmware (no float printf).
        """
        resp = resp.strip()
        if not resp.startswith("DATA:"):
            raise ValueError(f"Expected DATA: response, got: '{resp}'")
        result = {}
        for part in resp[5:].split(','):
            part = part.strip()
            if '=' not in part or not part:
                continue
            key, val = part.split('=', 1)
            key = key.strip()
            val = val.strip()
            if not val:
                continue
            try:
                result[key] = int(val) / 10000.0
            except ValueError:
                continue
        return result

    @staticmethod
    def _check(resp: str, context: str = ""):
        if resp.startswith("ERR:"):
            raise RuntimeError(
                f"Firmware error{' in ' + context if context else ''}: {resp}")

    # ── status ───────────────────────────────────────────────
    def status(self, chip: int = 1) -> dict:
        """
        Read chip health registers.

        Returns:
            dict with keys: ID, STAT, CLK1, CLK2, ENA
            ID should be 0x04 for ADS131A04.

        Example:
            s = adc.status(1)
            print(s)  # {'ID': '0x04', 'STAT': '0x00', ...}
        """
        resp = send_command(f"ADS_STATUS {chip}", port=self._port)
        self._check(resp, f"status(chip={chip})")
        # Parse OK:ADS1 ID=0x04 STAT=0x00 CLK1=0x02 CLK2=0x26 ENA=0x0F
        result = {}
        for part in resp[3:].split():
            if '=' in part:
                k, v = part.split('=', 1)
                result[k] = v
        return result

    # ── set_osr ──────────────────────────────────────────────
    def set_osr(self, chip: int, osr: int):
        """
        Change output data rate by setting OSR.

        Args:
            chip: 1 or 2
            osr:  one of 32, 64, 128, 256, 400, 512, 1024, 2048, 4096

        Data rates at fMOD=2MHz:
            32→62.5kSPS  64→32kSPS  128→16kSPS  256→8kSPS
            400→5kSPS    512→4kSPS  1024→2kSPS  2048→1kSPS  4096→0.5kSPS

        Example:
            adc.set_osr(1, 128)   # 16kSPS
        """
        if osr not in OSR_RATES:
            raise ValueError(f"OSR must be one of {list(OSR_RATES.keys())}")
        resp = send_command(f"ADS_CONFIG {chip} {osr}", port=self._port)
        self._check(resp, f"set_osr(chip={chip}, osr={osr})")
        rate = OSR_RATES[osr]
        print(f"[ADS131] Chip {chip} OSR={osr} → {rate/1000:.1f} kSPS")

    # ── read_single ──────────────────────────────────────────
    def read_single(self, chip: int = 1, ch: int = 1) -> float:
        """
        Read one voltage sample from one channel.

        Args:
            chip: 1 or 2
            ch:   1-4

        Returns:
            float voltage in volts (±2.442V range)

        Example:
            v = adc.read_single(1, 1)   # chip1, channel1
            v = adc.read_single(2, 3)   # chip2, channel3
        """
        resp = send_command(f"ADS_READ {chip} {ch}", port=self._port)
        self._check(resp, "read_single")
        data = self._parse_response(resp)
        key = f"C{chip}CH{ch}"
        if key not in data:
            raise ValueError(f"Key {key} not in response: {resp}")
        return self._apply_offset(chip, ch, data[key])

    # ── read_frame ───────────────────────────────────────────
    def read_frame(self, chip: int = 1) -> dict:
        """
        Read all 4 channels from one chip in a single conversion frame.

        Args:
            chip: 1 or 2

        Returns:
            dict {1: V, 2: V, 3: V, 4: V}

        Example:
            frame = adc.read_frame(1)
            print(f"CH1={frame[1]:.4f}V  CH2={frame[2]:.4f}V")
        """
        resp = send_command(f"ADS_READ {chip}", port=self._port)
        self._check(resp, "read_frame")
        data = self._parse_response(resp)
        result = {}
        for ch in self.CHANNELS:
            key = f"C{chip}CH{ch}"
            result[ch] = self._apply_offset(chip, ch, data.get(key, 0.0))
        return result

    # ── read_all ─────────────────────────────────────────────
    def read_all(self) -> dict:
        """
        Read all 8 channels from both chips.

        Returns:
            dict {'C1CH1': V, 'C1CH2': V, ..., 'C2CH4': V}

        Example:
            data = adc.read_all()
            for k, v in data.items():
                print(f"{k}: {v:.4f}V")
        """
        resp = send_command("ADS_READ ALL", port=self._port)
        self._check(resp, "read_all")
        return self._parse_response(resp)

    # ── read_buffered ────────────────────────────────────────
    def read_buffered(self,
                      chip: int = 1,
                      num_frames: int = 100) -> tuple:
        """
        Acquire a finite block of frames from one chip.
        Returns voltages for all 4 channels.

        Args:
            chip:       1 or 2
            num_frames: number of conversion frames to capture

        Returns:
            (voltages: np.ndarray shape (4, num_frames),
             timestamps: np.ndarray shape (num_frames,))
            voltages[0] = CH1, voltages[1] = CH2, etc.

        Example:
            v, t = adc.read_buffered(1, 1000)
            print(f"CH1 mean: {v[0].mean():.6f}V")
            print(f"Actual rate: {len(t)/t[-1]:.0f} SPS")
        """
        print(f"[ADS131] Buffered: {num_frames} frames from chip {chip}")

        voltages   = [[] for _ in range(4)]
        timestamps = []
        t_start    = None

        # Use streaming for efficiency
        resp = send_command(f"ADS_STREAM {chip} {num_frames}",
                            port=self._port)
        self._check(resp, "read_buffered stream start")

        # Collect frames until STREAM_DONE
        deadline = time.time() + num_frames * 0.01 + 10.0   # generous timeout
        while time.time() < deadline:
            raw = self._port.readline()
            if not raw:
                continue
            line = raw.decode('ascii', errors='replace').strip()
            if not line:
                continue
            if line.startswith("DATA:"):
                data = self._parse_response(line)
                now = time.time()
                if t_start is None:
                    t_start = now
                timestamps.append(now - t_start)
                for i, ch in enumerate(self.CHANNELS):
                    key = f"C{chip}CH{ch}"
                    voltages[i].append(data.get(key, 0.0))
            elif line.startswith("OK:ADS_STREAM_DONE"):
                break
            elif line.startswith("ERR:"):
                raise RuntimeError(f"Firmware error: {line}")

        v_arr = np.array(voltages, dtype=np.float64)
        t_arr = np.array(timestamps, dtype=np.float64)

        if len(t_arr) > 1:
            actual_rate = len(t_arr) / t_arr[-1]
            print(f"[ADS131] Done. {len(t_arr)} frames @ {actual_rate:.0f} SPS  "
                  f"CH1: min={v_arr[0].min():.4f}V max={v_arr[0].max():.4f}V "
                  f"mean={v_arr[0].mean():.6f}V")
        else:
            print("[ADS131] Warning: no frames received")

        return v_arr, t_arr

    # ── read_continuous ──────────────────────────────────────
    def read_continuous(self,
                        chip: int = 1,
                        ch: int = 1,
                        duration: float = None,
                        window_sec: float = 2.0,
                        csv_filename: str = None) -> tuple:
        """
        Live oscilloscope plot of one ADS131A04 channel.

        Args:
            chip:         1 or 2
            ch:           1-4 (channel to display in live plot)
            duration:     seconds, or None = until window closed
            window_sec:   rolling window width in seconds
            csv_filename: optional CSV save path

        Returns:
            (voltages: np.ndarray, timestamps: np.ndarray)
            voltages are for the selected display channel only.

        Example:
            v, t = adc.read_continuous(1, 1, duration=30)
        """
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        from matplotlib.widgets import Button

        print(f"[ADS131] Continuous: chip={chip} display_ch={ch}  "
              f"window={window_sec}s" +
              (f"  duration={duration}s" if duration else "  (indefinite)"))
        print("[ADS131] Close window or press STOP to end.")

        # Shared state
        all_voltages  = []   # display channel only
        all_times     = []
        stop_flag     = [False]
        lock          = threading.Lock()
        t_start       = [None]

        # Reader thread
        def _reader():
            resp = send_command(f"ADS_STREAM {chip} 0", port=self._port)
            if resp.startswith("ERR:"):
                print(f"[ADS131] {resp}")
                stop_flag[0] = True
                return

            warmup = [0]
            while not stop_flag[0]:
                try:
                    raw = self._port.readline()
                    if not raw:
                        continue
                    line = raw.decode('ascii', errors='replace').strip()
                    if not line or not line.startswith("DATA:"):
                        continue
                    data = self._parse_response(line)
                    key  = f"C{chip}CH{ch}"
                    v    = data.get(key, 0.0)
                    now  = time.time()
                    with lock:
                        if t_start[0] is None:
                            t_start[0] = now
                        if warmup[0] < 4:
                            warmup[0] += 1
                            continue
                        all_voltages.append(v)
                        all_times.append(now - t_start[0])
                except Exception as e:
                    if not stop_flag[0]:
                        print(f"[ADS131] Reader error: {e}")
                    break

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        # Plot
        fig, ax = plt.subplots(figsize=(11, 4))
        fig.patch.set_facecolor("#0d0d1a")
        ax.set_facecolor("#111122")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333355")
        ax.tick_params(colors="#aaaacc")
        ax.set_xlabel("Time (s)", color="#aaaacc")
        ax.set_ylabel("Voltage (V)", color="#aaaacc")
        ax.set_ylim(-VREF - 0.1, VREF + 0.1)
        ax.set_title(
            f"ADS131A04 — Chip{chip} CH{ch}  |  ±{VREF}V  |  window {window_sec}s" +
            (f"  |  {duration}s capture" if duration else "  |  live"),
            color="#ccccee", fontsize=9
        )
        ax.grid(True, color="#1a1a3a", linewidth=0.6)
        ax.axhline(0, color="#333355", linewidth=0.8, linestyle='--')

        line_plot, = ax.plot([], [], color="#00ffcc", linewidth=0.8)
        stats_text  = ax.text(0.01, 0.97, "", transform=ax.transAxes,
                              color="#aaaacc", fontsize=8, va="top",
                              family="monospace")

        ax_btn = fig.add_axes([0.44, 0.01, 0.12, 0.07])
        btn    = Button(ax_btn, "STOP", color="#5a0000", hovercolor="#8b0000")
        btn.label.set_color("white")
        btn.label.set_fontweight("bold")

        def _on_stop(e): stop_flag[0] = True
        btn.on_clicked(_on_stop)
        fig.canvas.mpl_connect("close_event",
                               lambda e: stop_flag.__setitem__(0, True))

        def _update(frame):
            with lock:
                if len(all_times) < 2:
                    return
                t_arr = np.array(all_times,    dtype=np.float64)
                v_arr = np.array(all_voltages, dtype=np.float64)

            t_now = t_arr[-1]
            t_min = max(0.0, t_now - window_sec)
            mask  = t_arr >= t_min
            line_plot.set_data(t_arr[mask], v_arr[mask])
            ax.set_xlim(t_min, t_now + window_sec * 0.02)

            if len(v_arr) > 0:
                stats_text.set_text(
                    f"n={len(t_arr)}  "
                    f"min={v_arr.min():.4f}V  max={v_arr.max():.4f}V  "
                    f"mean={v_arr.mean():.6f}V  "
                    f"rms={np.sqrt(np.mean(v_arr**2)):.6f}V  "
                    f"t={t_now:.1f}s"
                )

            if duration is not None and t_now >= duration:
                stop_flag[0] = True
            if stop_flag[0]:
                plt.close(fig)

        ani = animation.FuncAnimation(
            fig, _update, interval=50, blit=False, cache_frame_data=False
        )
        plt.tight_layout(rect=[0, 0.09, 1, 1])
        plt.show()

        stop_flag[0] = True
        try:
            send_command("ADS_STOP", port=self._port)
        except Exception:
            pass
        reader.join(timeout=2.0)

        with lock:
            v_final = np.array(all_voltages, dtype=np.float64)
            t_final = np.array(all_times,    dtype=np.float64)

        if len(v_final) > 0:
            rate = len(v_final) / t_final[-1] if t_final[-1] > 0 else 0
            print(f"[ADS131] Captured {len(v_final)} samples @ {rate:.0f} SPS  "
                  f"min={v_final.min():.4f}V  max={v_final.max():.4f}V  "
                  f"mean={v_final.mean():.6f}V")

        if csv_filename and len(v_final) > 0:
            np.savetxt(csv_filename,
                       np.column_stack([t_final, v_final]),
                       delimiter=",",
                       header="Time_s,Voltage_V",
                       comments="", fmt="%.8f")
            print(f"[ADS131] Saved {len(v_final)} samples → {csv_filename}")

        return v_final, t_final

    # ── read_dma ─────────────────────────────────────────────
    def read_dma(self,
                 chip: int = 1,
                 num_frames: int = 0,
                 duration: float = None,
                 window_sec: float = 2.0,
                 csv_filename: str = None,
                 display_ch: int = 1) -> tuple:
        """
        High-speed DMA binary streaming with live plot.

        Uses ADS_DMA_STREAM command. Firmware sends raw 15-byte SPI
        frames bundled in binary packets. Python unpacks directly to
        numpy — no ASCII parsing overhead.

        Packet format from firmware:
            [0]   'D' (0x44) — binary marker
            [1]   chip number
            [2-5] frame counter (uint32 big-endian)
            [6:]  N × 15 raw SPI bytes per frame

        Each 15-byte frame: [status 3B][CH1 3B][CH2 3B][CH3 3B][CH4 3B]
        24-bit signed, MSB first, two's complement.

        Args:
            chip:        1 or 2
            num_frames:  total frames to capture (0 = indefinite)
            duration:    stop after this many seconds (None = indefinite)
            window_sec:  live plot rolling window
            csv_filename: save path for CSV
            display_ch:  which channel (1-4) to show in live plot

        Returns:
            (voltages: np.ndarray shape (4, N),
             timestamps: np.ndarray shape (N,))

        Example:
            v, t = adc.read_dma(1, num_frames=10000)
            rate = len(t) / t[-1]
            print(f"Rate: {rate:.0f} SPS")
        """
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        from matplotlib.widgets import Button
        import struct

        FRAME_BYTES   = 15
        PKT_HEADER    = 6
        FRAMES_PER_PKT = 32

        print(f"[ADS131] DMA stream: chip={chip} ch={display_ch}  "
              f"window={window_sec}s" +
              (f"  n={num_frames}" if num_frames else "") +
              (f"  {duration}s" if duration else "  indefinite"))
        print("[ADS131] Close window or press STOP to end.")

        all_voltages = [[] for _ in range(4)]
        all_times    = []
        stop_flag    = [False]
        lock         = threading.Lock()
        t_start      = [None]

        def _parse_frame(raw15: bytes):
            """Unpack one 15-byte SPI frame into 4 signed voltages."""
            voltages = []
            for i in range(4):
                b = raw15[3 + i*3 : 6 + i*3]
                raw24 = (b[0] << 16) | (b[1] << 8) | b[2]
                if raw24 & 0x800000:
                    raw24 |= 0xFF000000
                    signed = raw24 - 0x100000000
                else:
                    signed = raw24
                voltages.append((signed / 8388608.0) * VREF)
            return voltages

        def _reader():
            # Send DMA stream start command
            n_arg = num_frames if num_frames else 0
            resp = send_command(f"ADS_DMA_STREAM {chip} {n_arg}",
                                port=self._port)
            if resp.startswith("ERR:"):
                print(f"[ADS131] {resp}")
                stop_flag[0] = True
                return

            warmup_frames = [0]
            buf = bytearray()

            while not stop_flag[0]:
                try:
                    chunk = self._port.read(self._port.in_waiting or 1)
                    if not chunk:
                        continue
                    buf.extend(chunk)

                    # Process complete packets from buffer
                    while len(buf) >= PKT_HEADER + FRAME_BYTES:

                        if buf[0] == ord('D'):
                            # Binary packet: D + chip(1) + counter(4) + N×15 bytes
                            # Scan forward to find where next packet or ASCII line starts
                            # to determine how many frames are in this packet.
                            # Search for next 'D' or 'O'/'E' after minimum packet size.
                            min_pkt = PKT_HEADER + FRAME_BYTES   # at least 1 frame
                            next_pkt = -1
                            for scan in range(min_pkt, len(buf)):
                                b = buf[scan]
                                if b == ord('D') or b == ord('O') or b == ord('E'):
                                    # Verify it could be a real packet start
                                    # (position aligns to frame boundary from header)
                                    payload_bytes = scan - PKT_HEADER
                                    if payload_bytes % FRAME_BYTES == 0:
                                        next_pkt = scan
                                        break

                            if next_pkt == -1:
                                # Haven't seen end of packet yet — wait for more data
                                # But if buffer is very large, just take what we have
                                if len(buf) < PKT_HEADER + FRAMES_PER_PKT * FRAME_BYTES + 10:
                                    break
                                # Force-consume up to FRAMES_PER_PKT frames
                                next_pkt = PKT_HEADER + min(
                                    FRAMES_PER_PKT,
                                    (len(buf) - PKT_HEADER) // FRAME_BYTES
                                ) * FRAME_BYTES

                            n_frames = (next_pkt - PKT_HEADER) // FRAME_BYTES
                            now = time.time()
                            with lock:
                                if t_start[0] is None:
                                    t_start[0] = now

                            for i in range(n_frames):
                                start = PKT_HEADER + i * FRAME_BYTES
                                frame_bytes = bytes(buf[start:start + FRAME_BYTES])
                                voltages = _parse_frame(frame_bytes)

                                for ch_idx in range(4):
                                    voltages[ch_idx] = self._apply_offset(
                                        chip, ch_idx + 1, voltages[ch_idx])

                                if warmup_frames[0] < 4:
                                    warmup_frames[0] += 1
                                    continue

                                with lock:
                                    for ch_idx in range(4):
                                        all_voltages[ch_idx].append(voltages[ch_idx])
                                    all_times.append(now - t_start[0])

                            buf = buf[next_pkt:]

                        elif buf[0] == ord('O') or buf[0] == ord('E'):
                            # ASCII response line (OK:/ERR:)
                            nl = buf.find(b'\n')
                            if nl == -1:
                                break
                            line = buf[:nl+1].decode('ascii', errors='replace').strip()
                            buf = buf[nl+1:]
                            if 'DONE' in line or 'STOP' in line:
                                stop_flag[0] = True
                                break
                        else:
                            buf = buf[1:]   # out of sync — skip byte

                except Exception as e:
                    if not stop_flag[0]:
                        print(f"[ADS131] DMA reader error: {e}")
                    break

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        # Live plot
        fig, ax = plt.subplots(figsize=(11, 4))
        fig.patch.set_facecolor("#0d0d1a")
        ax.set_facecolor("#111122")
        for spine in ax.spines.values():
            spine.set_edgecolor("#333355")
        ax.tick_params(colors="#aaaacc")
        ax.set_xlabel("Time (s)", color="#aaaacc")
        ax.set_ylabel("Voltage (V)", color="#aaaacc")
        ax.set_ylim(-VREF - 0.1, VREF + 0.1)
        ax.set_title(
            f"ADS131A04 DMA — Chip{chip} CH{display_ch}  "
            f"±{VREF}V  window={window_sec}s",
            color="#ccccee", fontsize=9)
        ax.grid(True, color="#1a1a3a", linewidth=0.6)
        ax.axhline(0, color="#333355", linewidth=0.8, linestyle='--')

        line_plot, = ax.plot([], [], color="#00ffcc", linewidth=0.6)
        stats_text  = ax.text(0.01, 0.97, "", transform=ax.transAxes,
                              color="#aaaacc", fontsize=8, va="top",
                              family="monospace")

        ax_btn = fig.add_axes([0.44, 0.01, 0.12, 0.07])
        btn    = Button(ax_btn, "STOP", color="#5a0000", hovercolor="#8b0000")
        btn.label.set_color("white")
        btn.label.set_fontweight("bold")
        btn.on_clicked(lambda e: stop_flag.__setitem__(0, True))
        fig.canvas.mpl_connect("close_event",
                               lambda e: stop_flag.__setitem__(0, True))

        def _update(frame_num):
            with lock:
                if len(all_times) < 2:
                    return
                t_arr = np.array(all_times,    dtype=np.float64)
                v_arr = np.array(all_voltages[display_ch-1], dtype=np.float64)

            t_now = t_arr[-1]
            t_min = max(0.0, t_now - window_sec)
            mask  = t_arr >= t_min
            line_plot.set_data(t_arr[mask], v_arr[mask])
            ax.set_xlim(t_min, t_now + window_sec * 0.02)

            rate = len(t_arr) / t_now if t_now > 0 else 0
            stats_text.set_text(
                f"n={len(t_arr)}  rate={rate:.0f} SPS  "
                f"min={v_arr.min():.4f}V  max={v_arr.max():.4f}V  "
                f"mean={v_arr.mean():.6f}V  t={t_now:.1f}s"
            )
            if duration and t_now >= duration:
                stop_flag[0] = True
            if num_frames and len(t_arr) >= num_frames:
                stop_flag[0] = True
            if stop_flag[0]:
                plt.close(fig)

        ani = animation.FuncAnimation(
            fig, _update, interval=50, blit=False, cache_frame_data=False)
        plt.tight_layout(rect=[0, 0.09, 1, 1])
        plt.show()

        stop_flag[0] = True
        try:
            send_command("ADS_DMA_STOP", port=self._port)
        except Exception:
            pass
        reader.join(timeout=3.0)

        with lock:
            v_final = np.array(all_voltages, dtype=np.float64)
            t_final = np.array(all_times,    dtype=np.float64)

        if len(t_final) > 1:
            rate = len(t_final) / t_final[-1]
            print(f"[ADS131] DMA: {len(t_final)} frames @ {rate:.0f} SPS  "
                  f"CH{display_ch}: "
                  f"min={v_final[display_ch-1].min():.4f}V  "
                  f"max={v_final[display_ch-1].max():.4f}V  "
                  f"mean={v_final[display_ch-1].mean():.6f}V")

        if csv_filename and len(t_final) > 0:
            data = np.column_stack([t_final] + [v_final[i] for i in range(4)])
            np.savetxt(csv_filename, data, delimiter=",",
                       header="Time_s,CH1_V,CH2_V,CH3_V,CH4_V",
                       comments="", fmt="%.8f")
            print(f"[ADS131] Saved {len(t_final)} frames → {csv_filename}")

        return v_final, t_final

    # ── dma_diagnostic ───────────────────────────────────────
    def dma_diagnostic(self, chip: int = 1, seconds: float = 2.0):
        """
        Raw diagnostic: start DMA stream, print first bytes received.
        Use this to see what's actually arriving before parsing.
        """
        import time
        print(f"[ADS131] DMA diagnostic: chip={chip}")
        resp = send_command(f"ADS_DMA_STREAM {chip} 0", port=self._port)
        print(f"[ADS131] Firmware ack: '{resp}'")
        time.sleep(0.1)

        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < seconds:
            waiting = self._port.in_waiting
            if waiting:
                buf.extend(self._port.read(waiting))
            if len(buf) >= 300:
                break
            time.sleep(0.001)

        try:
            send_command("ADS_DMA_STOP", port=self._port)
        except Exception:
            pass

        print(f"[ADS131] Received {len(buf)} bytes in {seconds:.1f}s")
        if len(buf) == 0:
            print("  NO DATA — DRDY EXTI not firing or DMA not running")
            print("  Verify: selftest() works, DRDY pins configured as EXTI_FALLING")
            return

        print(f"First 80 bytes hex: {buf[:80].hex(' ')}")
        printable = ''.join(chr(b) if 32 <= b < 127 else '.' for b in buf[:80])
        print(f"First 80 as ASCII:  '{printable}'")
        print(f"Count of 0x44 ('D'): {buf.count(0x44)}")
        print(f"Count of 0x4F ('O'): {buf.count(0x4F)}")

    # ── selftest ─────────────────────────────────────────────
    def selftest(self):
        """
        Read chip status registers and one frame from each chip.
        Good first test after bringup — inputs should be shorted for ≈0V.
        """
        print("[ADS131] Self-test:")
        for chip in self.CHIPS:
            try:
                s = self.status(chip)
                print(f"  Chip {chip} registers: {s}")
                if s.get('ID') != '0x04':
                    print(f"  *** WARNING: Chip {chip} ID={s.get('ID')} "
                          f"expected 0x04 — check SPI/CS wiring")
                    continue
                frame = self.read_frame(chip)
                for ch, v in frame.items():
                    print(f"  Chip {chip} CH{ch}: {v:+.6f} V")
            except Exception as e:
                print(f"  Chip {chip} ERROR: {e}")
        print("[ADS131] Self-test done.")


# ── Module-level convenience functions ───────────────────────
_default: ADS131 = None

def _get() -> ADS131:
    global _default
    if _default is None:
        _default = ADS131()
    return _default

def read_single(chip=1, ch=1):       return _get().read_single(chip, ch)
def read_frame(chip=1):              return _get().read_frame(chip)
def read_all():                      return _get().read_all()
def read_buffered(chip=1, n=100):    return _get().read_buffered(chip, n)
def selftest():                      return _get().selftest()


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    adc = ADS131()
    adc.selftest()
    print("\nSingle reads:")
    print(f"  Chip1 CH1: {adc.read_single(1,1):+.6f} V")
    print(f"  Chip2 CH1: {adc.read_single(2,1):+.6f} V")
    print("\nAll 8 channels:")
    for k, v in adc.read_all().items():
        print(f"  {k}: {v:+.6f} V")