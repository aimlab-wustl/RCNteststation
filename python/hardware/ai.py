# ============================================================
# hardware/ai.py — Analog Input
# Covers:
#   • read_single()      — one voltage value per channel
#   • read_buffered()    — finite high-speed acquisition
#   • read_continuous()  — indefinite streaming with live oscilloscope plot
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import threading
import time
import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration
from config import (
    DEVICE,
    AI_CHANNELS,
    AI_TERMINAL_CONFIG,
    AI_VOLTAGE_RANGE,
    AI_DEFAULT_RATE,
    AI_DEFAULT_SAMPLES,
)

_TERMINAL_MAP = {
    "SingleEnded":  TerminalConfiguration.RSE,
    "Differential": TerminalConfiguration.DIFF,
    "Pseudodiff":   TerminalConfiguration.PSEUDO_DIFF,
}


def _terminal_config() -> TerminalConfiguration:
    cfg = _TERMINAL_MAP.get(AI_TERMINAL_CONFIG)
    if cfg is None:
        raise ValueError(f"Unknown AI_TERMINAL_CONFIG: '{AI_TERMINAL_CONFIG}'")
    return cfg


# ── Single scan ───────────────────────────────────────────────

def read_single(
    channels=None,
    device: str = DEVICE,
):
    """
    Read one voltage sample from each requested channel.

    Args:
        channels: int, list of ints, or None (all AI_CHANNELS)
        device:   DAQ device name

    Returns:
        float if single channel, list[float] if multiple

    Example:
        v0         = read_single(0)
        v0, v1, v2 = read_single([0, 1, 2])
        all_ch     = read_single()
    """
    if channels is None:
        channels = AI_CHANNELS
    single = isinstance(channels, int)
    channels = [channels] if single else list(channels)
    ch_str = ", ".join(f"{device}/ai{c}" for c in channels)

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(
            ch_str,
            min_val=AI_VOLTAGE_RANGE[0],
            max_val=AI_VOLTAGE_RANGE[1],
            terminal_config=_terminal_config(),
        )
        result = task.read()

    if single:
        return float(result) if not isinstance(result, list) else float(result[0])
    return [float(v) for v in result] if isinstance(result, list) else [float(result)]


# ── Finite buffered acquisition ───────────────────────────────

def read_buffered(
    channel: int = 0,
    rate: int = AI_DEFAULT_RATE,
    num_samples: int = AI_DEFAULT_SAMPLES,
    device: str = DEVICE,
) -> tuple:
    """
    Finite high-speed acquisition on a single channel.
    All samples held in RAM — suitable for up to ~minutes at 400 kS/s.
    For longer / indefinite acquisition use read_continuous().

    Args:
        channel:     ai channel index (single ch = max rate)
        rate:        sample rate in Hz  (max 400 000 on USB-6212 single ch)
        num_samples: total samples to acquire
        device:      DAQ device name

    Returns:
        (voltages: np.ndarray, timestamps: np.ndarray)
        timestamps in seconds from 0.

    Example:
        volts, times = read_buffered(channel=0, rate=400_000, num_samples=4000)
    """
    ch_str = f"{device}/ai{channel}"
    duration_s = num_samples / rate

    print(f"[ai] Finite: {num_samples} samples @ {rate/1000:.0f} kS/s "
          f"on ai{channel}  ({duration_s*1000:.1f} ms)")

    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(
            ch_str,
            min_val=AI_VOLTAGE_RANGE[0],
            max_val=AI_VOLTAGE_RANGE[1],
            terminal_config=_terminal_config(),
        )
        task.timing.cfg_samp_clk_timing(
            rate=rate,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=num_samples,
        )
        raw = task.read(number_of_samples_per_channel=num_samples,
                        timeout=duration_s + 5.0)

    voltages   = np.array(raw, dtype=np.float64)
    timestamps = np.arange(len(voltages)) / rate

    print(f"[ai] Done.  Min={voltages.min():.4f}V  "
          f"Max={voltages.max():.4f}V  Mean={voltages.mean():.4f}V")

    return voltages, timestamps


# ── Continuous streaming acquisition ─────────────────────────

def read_continuous(
    channel: int = 0,
    rate: int = AI_DEFAULT_RATE,
    duration: float = None,
    window_sec: float = 0.5,
    chunk_sec: float = 0.1,
    csv_filename: str = None,
    device: str = DEVICE,
) -> tuple:
    """
    Indefinite (or duration-limited) streaming acquisition with live
    oscilloscope plot. Mirrors MATLAB AIcompleteworking.m.

    The DAQ hardware clock runs at `rate` Hz continuously. Python receives
    data in chunks via a callback — no samples are dropped between chunks.
    Memory usage is bounded: only `window_sec` of data is kept for plotting;
    all samples are optionally saved to CSV.

    Args:
        channel:      ai channel index
        rate:         sample rate in Hz
        duration:     seconds to run, or None to run until window is closed
        window_sec:   oscilloscope time window width in seconds
        chunk_sec:    how often the callback fires (smaller = more responsive)
        csv_filename: path to save CSV, or None to skip saving
        device:       DAQ device name

    Returns:
        (voltages: np.ndarray, timestamps: np.ndarray)
        — the full acquired data (up to duration, or until stopped)

    Example:
        # Run for 10 seconds, show live plot, save to CSV
        v, t = read_continuous(channel=0, rate=400_000, duration=10,
                               csv_filename='capture.csv')

        # Run until user closes the window
        v, t = read_continuous(channel=0, rate=10_000)
    """
    import matplotlib
    matplotlib.use("TkAgg")          # works on Windows with standard Python
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation

    chunk_size    = max(1000, int(rate * chunk_sec))
    window_pts    = int(rate * window_sec)

    # ── Shared state (written by DAQ callback, read by plot) ──
    # Pre-allocate a ring buffer for plotting (bounded memory)
    ring_buf      = np.zeros(window_pts, dtype=np.float32)
    ring_time     = np.zeros(window_pts, dtype=np.float64)
    ring_write    = [0]          # next write position (list so callback can mutate)

    # Growing arrays for full data (only if we need to return or save it)
    all_data      = []
    all_time      = []
    total_samples = [0]

    stop_flag     = [False]
    lock          = threading.Lock()

    # ── DAQ callback ─────────────────────────────────────────
    # NOTE: on Windows, task_handle is a raw int (C handle), NOT the
    # nidaqmx Task object. Read via the outer `task` variable (closure).
    task_ref = [None]   # filled in after task is created

    def _callback(task_handle, every_n_samples_event_type,
                  number_of_samples, callback_data):
        try:
            if stop_flag[0]:
                return 0
            chunk = task_ref[0].read(number_of_samples_per_channel=number_of_samples)
            chunk = np.array(chunk, dtype=np.float32)
            n     = len(chunk)
            t0    = total_samples[0] / rate
            times = t0 + np.arange(n, dtype=np.float64) / rate

            with lock:
                # ring buffer (for plot)
                for i in range(n):
                    idx = ring_write[0] % window_pts
                    ring_buf[idx]  = chunk[i]
                    ring_time[idx] = times[i]
                    ring_write[0] += 1

                # full data store
                all_data.append(chunk)
                all_time.append(times)
                total_samples[0] += n

            if duration is not None and total_samples[0] >= int(rate * duration):
                stop_flag[0] = True
        except Exception as e:
            print(f"[ai] Callback error: {e}")
            stop_flag[0] = True
        return 0

    # ── Plot setup ────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#1e1e1e")
    ax.set_facecolor("#1e1e1e")
    ax.tick_params(colors="#aaaaaa")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444444")
    ax.set_xlabel("Time (s)", color="#aaaaaa")
    ax.set_ylabel("Voltage (V)", color="#aaaaaa")

    vmin, vmax = AI_VOLTAGE_RANGE
    ax.set_ylim(vmin - 0.1, vmax + 0.1)
    ax.grid(True, color="#333333", linewidth=0.5)

    line, = ax.plot([], [], color="#00d4aa", linewidth=0.8)

    # Stats text
    stats_text = ax.text(
        0.01, 0.97, "", transform=ax.transAxes,
        color="#aaaaaa", fontsize=8, va="top", family="monospace"
    )

    # STOP button
    from matplotlib.widgets import Button
    ax_btn = fig.add_axes([0.45, 0.01, 0.1, 0.06])
    btn = Button(ax_btn, "STOP", color="#aa2222", hovercolor="#cc3333")
    btn.label.set_color("white")
    btn.label.set_fontweight("bold")

    title_str = (f"ai{channel}  |  {rate/1000:.0f} kS/s  |  "
                 f"window: {window_sec:.1f}s"
                 + (f"  |  duration: {duration}s" if duration else "  |  running"))
    ax.set_title(title_str, color="#cccccc", fontsize=9)

    def _on_stop(event):
        stop_flag[0] = True

    btn.on_clicked(_on_stop)
    fig.canvas.mpl_connect("close_event", lambda e: stop_flag.__setitem__(0, True))

    # ── Animation update ──────────────────────────────────────
    def _update(frame):
        with lock:
            w      = ring_write[0]
            filled = min(w, window_pts)
            if filled == 0:
                return
            if w < window_pts:
                y = ring_buf[:filled].copy()
                t = ring_time[:filled].copy()
            else:
                end = w % window_pts
                y   = np.roll(ring_buf,  -end)
                t   = np.roll(ring_time, -end)
            n_total = total_samples[0]

        if len(t) < 2:
            return

        t_now = t[-1]
        t_min = t_now - window_sec

        # Plot with elapsed-second values on x — axis ticks show real seconds
        line.set_data(t, y)
        ax.set_xlim(t_min, t_now + window_sec * 0.02)

        # Re-label x ticks as elapsed seconds (e.g. 1.0, 1.5, 2.0 ...)
        tick_vals = np.linspace(t_min, t_now, 6)
        ax.set_xticks(tick_vals)
        ax.set_xticklabels([f"{v:.2f}" for v in tick_vals], color="#aaaaaa")

        seg = y if w >= window_pts else y[y != 0]
        if len(seg) == 0:
            seg = y
        stats_text.set_text(
            f"min={seg.min():.3f}V  max={seg.max():.3f}V  "
            f"mean={seg.mean():.3f}V  rms={np.sqrt(np.mean(seg**2)):.3f}V  "
            f"t={n_total/rate:.2f}s"
        )

        fig.canvas.draw_idle()   # redraw axes frame (needed since blit=False)

        if stop_flag[0]:
            plt.close(fig)

    ani = animation.FuncAnimation(
        fig, _update, interval=50, blit=False, cache_frame_data=False
    )

    # ── Start DAQ ─────────────────────────────────────────────
    print(f"[ai] Continuous: ai{channel} @ {rate/1000:.0f} kS/s  "
          f"chunk={chunk_size}  window={window_sec}s")
    print("[ai] Close the plot window or press STOP to end acquisition.")

    task = nidaqmx.Task()
    task_ref[0] = task          # give callback access to the Task object
    task.ai_channels.add_ai_voltage_chan(
        f"{device}/ai{channel}",
        min_val=AI_VOLTAGE_RANGE[0],
        max_val=AI_VOLTAGE_RANGE[1],
        terminal_config=_terminal_config(),
    )
    task.timing.cfg_samp_clk_timing(
        rate=rate,
        sample_mode=AcquisitionType.CONTINUOUS,
    )
    task.register_every_n_samples_acquired_into_buffer_event(chunk_size, _callback)

    start_time = time.time()
    task.start()

    try:
        plt.tight_layout(rect=[0, 0.08, 1, 1])
        plt.show()          # blocks here until window is closed
    finally:
        stop_flag[0] = True
        task.stop()
        task.close()

    elapsed = time.time() - start_time
    print(f"[ai] Acquisition ended.  "
          f"Total: {total_samples[0]} samples ({elapsed:.1f}s)")

    # ── Assemble full data arrays ─────────────────────────────
    if all_data:
        voltages   = np.concatenate(all_data).astype(np.float64)
        timestamps = np.concatenate(all_time)
        print(f"[ai] Min={voltages.min():.4f}V  Max={voltages.max():.4f}V  "
              f"Mean={voltages.mean():.4f}V")
    else:
        voltages   = np.array([], dtype=np.float64)
        timestamps = np.array([], dtype=np.float64)

    # ── Optional CSV save ─────────────────────────────────────
    if csv_filename and len(voltages) > 0:
        print(f"[ai] Saving {len(voltages)} samples to {csv_filename}...")
        header = "Time_s,Voltage_V"
        np.savetxt(csv_filename,
                   np.column_stack([timestamps, voltages]),
                   delimiter=",", header=header, comments="", fmt="%.8f")
        print(f"[ai] Saved.")

    return voltages, timestamps


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    print("Single scan ai0:", read_single(0))
    v, t = read_buffered(channel=0, rate=10_000, num_samples=1_000)
    print(f"Buffered: {len(v)} samples, {t[-1]*1000:.1f} ms")
    v, t = read_continuous(channel=0, rate=10_000, window_sec=1.0, duration=5)
    print(f"Continuous: {len(v)} samples")