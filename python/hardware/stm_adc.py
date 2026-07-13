# ============================================================
# hardware/stm_adc.py — STM32 Onboard ADC  (PA1–PA4)
# AIMLAB_TESTSTATION_ADC_V1
#
# Reads the STM32H743 internal ADC channels via USB CDC.
# Channels 1-4 map to PA1-PA4 (0–3.3V range, 16-bit, ~1kSPS via CDC).
#
# API:
#   read_single(channel)          → float or dict
#   read_buffered(channel, n)     → (np.ndarray voltages, np.ndarray times)
#   read_continuous(channel, ...) → live oscilloscope plot + returns arrays
#
# Usage:
#   from hardware.stm_adc import STMADC
#   adc = STMADC()
#   v = adc.read_single(1)           # read PA1 once
#   v = adc.read_single("ALL")       # read PA1-PA4 as dict
#   v, t = adc.read_buffered(1, 500) # 500 samples from PA1
#   adc.read_continuous(1)           # live plot until closed
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import threading
import numpy as np

from hardware.cdc_serial import open_port, send_command, send_command_multi, ping
from config import STM_COM_PORT, STM_BAUD_RATE, STM_TIMEOUT


class STMADC:
    """
    STM32 onboard ADC interface over USB CDC.

    Channels 1–4 → PA1–PA4, range 0–3.3V.
    Use channel=0 or "ALL" to read all four simultaneously.
    """

    VREF       = 3.3          # STM32H743 ADC reference voltage
    CHANNELS   = [1, 2, 3, 4]
    CH_LABELS  = {1: "PA1", 2: "PA2", 3: "PA3", 4: "PA4"}

    def __init__(self,
                 port: str   = STM_COM_PORT,
                 baud: int   = STM_BAUD_RATE,
                 timeout: float = STM_TIMEOUT):
        self._port = open_port(port, baud, timeout)
        if not ping(self._port):
            raise RuntimeError(
                f"STM32 board not responding on {port}. "
                "Check USB cable and firmware.")
        print(f"[STMADC] Connected on {port}")

    # ── Internal: parse DATA response ───────────────────────
    @staticmethod
    def _parse_data(resp: str) -> dict:
        """
        Parse firmware DATA response into {ch: voltage_float} dict.

        Firmware sends integer values scaled by 10000 (avoids newlib-nano
        float printf limitation). e.g. DATA:ch1=16500,ch2=0 means 1.6500V.

        Also handles plain float format if -u _printf_float linker flag
        is ever enabled in future.
        """
        resp = resp.strip().rstrip('\r\n')

        if not resp.startswith("DATA:"):
            raise ValueError(f"Unexpected response: '{resp}'")

        payload = resp[5:]
        result = {}
        for part in payload.split(','):
            part = part.strip().rstrip('\r\n')
            if not part:
                continue
            if '=' not in part:
                continue
            key, val = part.split('=', 1)
            key = key.strip()
            val = val.strip()
            if not val or not key.startswith('ch'):
                continue
            try:
                ch_num = int(key[2:])
                raw = val.rstrip('V')   # strip trailing V if present
                # Integer encoding: divide by 10000 to get volts
                # Float encoding: parse directly (future-proof)
                if '.' in raw:
                    result[ch_num] = float(raw)
                else:
                    result[ch_num] = int(raw) / 10000.0
            except (ValueError, IndexError):
                continue
        return result

    # ── read_single ─────────────────────────────────────────
    def read_single(self, channel=1):
        """
        Read one sample from the STM32 onboard ADC.

        Args:
            channel: int 1-4, or "ALL" / 0 for all four channels.

        Returns:
            float  — if single channel
            dict   — {1: V, 2: V, 3: V, 4: V} if ALL

        Example:
            v1          = adc.read_single(1)
            all_voltages = adc.read_single("ALL")
        """
        if str(channel).upper() in ("ALL", "0"):
            cmd = "STMADC ALL"
        else:
            ch = int(channel)
            if ch not in self.CHANNELS:
                raise ValueError(f"Channel must be 1-4 or ALL, got {channel}")
            cmd = f"STMADC {ch}"

        resp = send_command(cmd, port=self._port)
        data = self._parse_data(resp)

        if str(channel).upper() in ("ALL", "0"):
            return data
        return data[int(channel)]

    # ── read_buffered ────────────────────────────────────────
    def read_buffered(self,
                      channel: int = 1,
                      num_samples: int = 100,
                      rate_hz: float = None) -> tuple:
        """
        Acquire a finite block of samples from one STM32 ADC channel.

        The STM32 streams samples as fast as USB CDC allows (~1kSPS).
        If rate_hz is set, a delay is inserted between samples in firmware
        to approximate the requested rate (max ~1000 Hz via CDC).

        Args:
            channel:     1-4 (PA1-PA4)
            num_samples: total samples to acquire
            rate_hz:     target rate in Hz, or None for max speed

        Returns:
            (voltages: np.ndarray, timestamps: np.ndarray)
            timestamps in seconds from 0.

        Example:
            v, t = adc.read_buffered(1, 500)
            print(f"Mean: {v.mean():.4f}V")
        """
        if channel not in self.CHANNELS:
            raise ValueError(f"Channel must be 1-4, got {channel}")

        print(f"[STMADC] Buffered: {num_samples} samples, ch={channel} (PA{channel})")

        # Send stream command — firmware sends n samples then OK:STREAM_DONE
        cmd = f"STMADC_STREAM {channel} {num_samples}"

        # Timeout: n samples at ~1kSPS + 5s margin
        timeout_s = (num_samples / 1000.0) + 5.0

        lines = send_command_multi(cmd,
                                   timeout_s=timeout_s,
                                   port=self._port)

        voltages   = []
        timestamps = []
        t_start    = None

        for line in lines:
            if line.startswith("DATA:"):
                data = self._parse_data(line)
                v = data.get(channel, 0.0)
                voltages.append(v)
                now = time.time()
                if t_start is None:
                    t_start = now
                timestamps.append(now - t_start)
            elif line.startswith("ERR:"):
                raise RuntimeError(f"Firmware error: {line}")
            # OK:STREAM_START and OK:STREAM_DONE are silently consumed

        v_arr = np.array(voltages,   dtype=np.float64)
        t_arr = np.array(timestamps, dtype=np.float64)

        if len(v_arr) == 0:
            print("[STMADC] Warning: no samples received")
            return v_arr, t_arr

        actual_rate = len(v_arr) / t_arr[-1] if t_arr[-1] > 0 else 0
        print(f"[STMADC] Done. {len(v_arr)} samples  "
              f"CDC throughput ~{actual_rate:.0f} sps  "
              f"Min={v_arr.min():.4f}V  Max={v_arr.max():.4f}V  "
              f"Mean={v_arr.mean():.4f}V  "
              f"(HW ADC rate ~438kSPS, CDC-limited)")

        return v_arr, t_arr

    # ── read_continuous ──────────────────────────────────────
    def read_continuous(self,
                        channel: int = 1,
                        duration: float = None,
                        window_sec: float = 2.0,
                        csv_filename: str = None) -> tuple:
        """
        Live oscilloscope plot of STM32 onboard ADC.
        Streams from firmware until window is closed or duration expires.

        Args:
            channel:      1-4 (PA1-PA4)
            duration:     seconds to run, or None = until window closed
            window_sec:   oscilloscope rolling window width in seconds
            csv_filename: optional path to save captured data as CSV

        Returns:
            (voltages: np.ndarray, timestamps: np.ndarray)

        Example:
            v, t = adc.read_continuous(1, duration=10)
            v, t = adc.read_continuous(2)   # run until window closed
        """
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        from matplotlib.widgets import Button

        if channel not in self.CHANNELS:
            raise ValueError(f"Channel must be 1-4, got {channel}")

        print(f"[STMADC] Continuous: ch={channel} (PA{channel})  "
              f"window={window_sec}s" +
              (f"  duration={duration}s" if duration else "  (indefinite)"))
        print("[STMADC] Close plot window or press STOP to end.")

        # ── Shared state ─────────────────────────────────────
        all_voltages  = []
        all_times     = []
        stop_flag     = [False]
        lock          = threading.Lock()
        t_start       = [None]

        # ── Reader thread — pulls lines from serial ──────────
        def _reader():
            # Start indefinite stream
            resp = send_command(f"STMADC_STREAM {channel} 0",
                                port=self._port)
            if resp.startswith("ERR:"):
                print(f"[STMADC] {resp}")
                stop_flag[0] = True
                return

            while not stop_flag[0]:
                try:
                    raw = self._port.readline()
                    if not raw:
                        continue
                    line = raw.decode('ascii', errors='replace').strip()
                    if not line:
                        continue
                    if line.startswith("DATA:"):
                        data = self._parse_data(line)
                        v = data.get(channel, 0.0)
                        now = time.time()
                        with lock:
                            if t_start[0] is None:
                                t_start[0] = now
                                # Skip first 20 samples — STM32 ADC needs
                                # a few conversions to settle after stream start
                                _warmup = [0]
                            if _warmup[0] < 20:
                                _warmup[0] += 1
                                continue
                            all_voltages.append(v)
                            all_times.append(now - t_start[0])
                    elif line.startswith("ERR:"):
                        print(f"[STMADC] Firmware error: {line}")
                        stop_flag[0] = True
                except Exception as e:
                    if not stop_flag[0]:
                        print(f"[STMADC] Reader error: {e}")
                    break

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        # ── Plot setup ────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(11, 4))
        fig.patch.set_facecolor("#1a1a2e")
        ax.set_facecolor("#16213e")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444466")
        ax.tick_params(colors="#aaaacc")
        ax.set_xlabel("Time (s)", color="#aaaacc")
        ax.set_ylabel("Voltage (V)", color="#aaaacc")
        ax.set_ylim(-0.1, self.VREF + 0.1)
        ax.set_title(
            f"STMADC — ch{channel} ({self.CH_LABELS[channel]})  "
            f"| 0–{self.VREF}V | window {window_sec}s" +
            (f" | {duration}s capture" if duration else " | live"),
            color="#ccccee", fontsize=9
        )
        ax.grid(True, color="#2a2a4a", linewidth=0.6)

        line_plot, = ax.plot([], [], color="#00e5cc", linewidth=0.9)
        stats_text  = ax.text(0.01, 0.97, "", transform=ax.transAxes,
                              color="#aaaacc", fontsize=8, va="top",
                              family="monospace")

        ax_btn = fig.add_axes([0.44, 0.01, 0.12, 0.07])
        btn    = Button(ax_btn, "STOP", color="#8b0000", hovercolor="#cc0000")
        btn.label.set_color("white")
        btn.label.set_fontweight("bold")

        def _on_stop(event):
            stop_flag[0] = True
        btn.on_clicked(_on_stop)
        fig.canvas.mpl_connect("close_event",
                               lambda e: stop_flag.__setitem__(0, True))

        # ── Animation update ──────────────────────────────────
        def _update(frame):
            with lock:
                if len(all_times) < 2:
                    return
                t_arr = np.array(all_times,    dtype=np.float64)
                v_arr = np.array(all_voltages, dtype=np.float64)

            t_now  = t_arr[-1]
            t_min  = max(0.0, t_now - window_sec)
            mask   = t_arr >= t_min
            t_win  = t_arr[mask]
            v_win  = v_arr[mask]

            line_plot.set_data(t_win, v_win)
            ax.set_xlim(t_min, t_now + window_sec * 0.02)

            if len(v_win) > 0:
                stats_text.set_text(
                    f"n={len(t_arr)}  "
                    f"min={v_arr.min():.4f}V  max={v_arr.max():.4f}V  "
                    f"mean={v_arr.mean():.4f}V  "
                    f"t={t_now:.1f}s"
                )

            # Duration check
            if duration is not None and t_now >= duration:
                stop_flag[0] = True
            if stop_flag[0]:
                plt.close(fig)

        ani = animation.FuncAnimation(
            fig, _update, interval=50, blit=False, cache_frame_data=False
        )

        plt.tight_layout(rect=[0, 0.09, 1, 1])
        plt.show()   # blocks until window closed

        # ── Stop stream ───────────────────────────────────────
        stop_flag[0] = True
        try:
            send_command("STMADC_STOP", port=self._port)
        except Exception:
            pass
        reader_thread.join(timeout=2.0)

        # ── Assemble results ──────────────────────────────────
        with lock:
            v_final = np.array(all_voltages, dtype=np.float64)
            t_final = np.array(all_times,    dtype=np.float64)

        if len(v_final) > 0:
            print(f"[STMADC] Captured {len(v_final)} samples  "
                  f"Min={v_final.min():.4f}V  Max={v_final.max():.4f}V  "
                  f"Mean={v_final.mean():.4f}V")
        else:
            print("[STMADC] No samples captured.")

        if csv_filename and len(v_final) > 0:
            np.savetxt(csv_filename,
                       np.column_stack([t_final, v_final]),
                       delimiter=",",
                       header="Time_s,Voltage_V",
                       comments="", fmt="%.8f")
            print(f"[STMADC] Saved {len(v_final)} samples → {csv_filename}")

        return v_final, t_final

    # ── Quick self-test ───────────────────────────────────────
    def selftest(self):
        """Read all 4 channels once and print results."""
        print("[STMADC] Self-test — reading PA1–PA4:")
        data = self.read_single("ALL")
        for ch, v in data.items():
            print(f"  ch{ch} ({self.CH_LABELS[ch]}): {v:.4f} V")
        return data


# ── Module-level convenience functions ───────────────────────
# These mirror the ai.py style so existing test scripts
# can call STMADC functions without instantiating the class.

_default_adc: STMADC = None

def _get_default() -> STMADC:
    global _default_adc
    if _default_adc is None:
        _default_adc = STMADC()
    return _default_adc

def read_single(channel=1):
    return _get_default().read_single(channel)

def read_buffered(channel=1, num_samples=100):
    return _get_default().read_buffered(channel, num_samples)

def read_continuous(channel=1, duration=None, window_sec=2.0, csv_filename=None):
    return _get_default().read_continuous(channel, duration, window_sec, csv_filename)


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    adc = STMADC()
    adc.selftest()
    print("\nBuffered 50 samples from PA1:")
    v, t = adc.read_buffered(1, 50)
    print(f"  {len(v)} samples  mean={v.mean():.4f}V  "
          f"duration={t[-1]*1000:.1f}ms")
    print("\nStarting live plot (close window to exit):")
    adc.read_continuous(1, window_sec=3.0)