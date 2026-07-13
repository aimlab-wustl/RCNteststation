# ============================================================
# hardware/pfi.py — Counter / PFI functions
# USB-6212 has 2 counters (ctr0, ctr1) and 16 PFI lines.
#
# Functions:
#   generate_pulse()        — output continuous pulse train (like DOfast.m ctr0)
#   stop_pulse()            — stop a running pulse task
#   count_edges()           — count rising edges on a PFI line (frequency/tach)
#   measure_frequency()     — one-shot frequency measurement on a PFI line
#   arm_ai_trigger()        — configure AI to start on PFI rising edge
#
# USB-6212 counter output pin:
#   ctr0 out → PFI12  (pin 2  on the connector, labelled PFI12/P2.4)
#   ctr1 out → PFI13  (pin 40 on the connector, labelled PFI13/P2.5)
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import nidaqmx
from nidaqmx.constants import (
    AcquisitionType,
    Edge,
    CountDirection,
    CounterFrequencyMethod,
    FrequencyUnits,
    TerminalConfiguration,
)
from config import DEVICE


# ── Pulse generation ──────────────────────────────────────────

def generate_pulse(
    frequency: float,
    duty_cycle: float = 0.5,
    counter: str = "ctr0",
    output_pfi_line: int = 2,    # reroute output to this PFI line (default PFI2)
    device: str = DEVICE,
) -> nidaqmx.Task:
    """
    Start a continuous hardware pulse train on a counter output.
    Mirrors MATLAB: addoutput(dq, dev, "ctr0", "PulseGeneration")

    By default the output is rerouted to PFI2 (accessible pin).
    The hardware default would be PFI12 for ctr0, PFI13 for ctr1,
    but those pins may not be accessible on all breakout configurations.

    Args:
        frequency:       pulse frequency in Hz  (e.g. 1000 = 1 kHz)
        duty_cycle:      0.0–1.0  (default 0.5 = square wave)
        counter:         "ctr0" or "ctr1"
        output_pfi_line: PFI line number to route output to (default 2)
        device:          DAQ device name

    Returns:
        The running nidaqmx.Task — caller must call stop_pulse(task) when done.

    Example:
        task = generate_pulse(frequency=10_000, duty_cycle=0.5, output_pfi_line=2)
        time.sleep(1.0)
        stop_pulse(task)
    """
    task = nidaqmx.Task()
    ch = task.co_channels.add_co_pulse_chan_freq(
        f"{device}/{counter}",
        freq=frequency,
        duty_cycle=duty_cycle,
        idle_state=nidaqmx.constants.Level.LOW,
    )
    # Reroute counter output from default pin to the requested PFI line
    ch.co_pulse_term = f"/{device}/PFI{output_pfi_line}"
    task.timing.cfg_implicit_timing(
        sample_mode=AcquisitionType.CONTINUOUS,
    )
    task.start()
    print(f"[pfi] Pulse running: {counter}  {frequency:.1f} Hz  "
          f"duty={duty_cycle*100:.0f}%  → PFI{output_pfi_line}")
    return task


def stop_pulse(task: nidaqmx.Task) -> None:
    """Stop and close a pulse task returned by generate_pulse()."""
    task.stop()
    task.close()
    print("[pfi] Pulse stopped.")


# ── Edge counting ─────────────────────────────────────────────

def count_edges(
    duration: float,
    pfi_line: int = 0,
    edge: str = "rising",
    counter: str = "ctr1",   # ctr1 by default — ctr0 is often busy with pulse gen
    device: str = DEVICE,
) -> int:
    """
    Count edges on a PFI line over a fixed time window.
    Useful for encoder counts, event counting, tachometer.

    Args:
        duration:   counting window in seconds
        pfi_line:   PFI line number for the input signal (0–15)
        edge:       "rising" or "falling"
        counter:    "ctr0" or "ctr1"
        device:     DAQ device name

    Returns:
        Integer count of edges detected.

    Example:
        # Count pulses on PFI0 for 1 second → gives frequency in Hz
        n = count_edges(duration=1.0, pfi_line=0)
        print(f"Frequency: {n} Hz")
    """
    edge_const = Edge.RISING if edge == "rising" else Edge.FALLING
    src = f"/{device}/PFI{pfi_line}"

    with nidaqmx.Task() as task:
        task.ci_channels.add_ci_count_edges_chan(
            f"{device}/{counter}",
            edge=edge_const,
            count_direction=CountDirection.COUNT_UP,
        )
        task.ci_channels[0].ci_count_edges_term = src
        task.start()
        time.sleep(duration)
        count = task.read()
        task.stop()

    print(f"[pfi] Counted {count} {edge} edges on PFI{pfi_line} "
          f"over {duration:.3f}s  (~{count/duration:.1f} Hz)")
    return int(count)


# ── Frequency measurement ─────────────────────────────────────

def measure_frequency(
    pfi_line: int = 0,
    meas_time: float = 0.1,
    counter: str = "ctr1",   # ctr1 by default — ctr0 is often busy with pulse gen
    device: str = DEVICE,
) -> float:
    """
    Measure the frequency of a signal on a PFI line.
    Uses the hardware frequency measurement mode — more accurate
    than count_edges() for short windows.

    Args:
        pfi_line:  PFI line number carrying the signal (0–15)
        meas_time: measurement gate time in seconds (longer = more accurate)
        counter:   "ctr0" or "ctr1"
        device:    DAQ device name

    Returns:
        Measured frequency in Hz.

    Example:
        freq = measure_frequency(pfi_line=0, meas_time=0.5)
        print(f"Signal frequency: {freq:.2f} Hz")
    """
    src = f"/{device}/PFI{pfi_line}"

    with nidaqmx.Task() as task:
        ch = task.ci_channels.add_ci_freq_chan(
            f"{device}/{counter}",
            min_val=2.0,
            max_val=1_000_000.0,
            units=nidaqmx.constants.FrequencyUnits.HZ,
            edge=Edge.RISING,
            meas_method=nidaqmx.constants.CounterFrequencyMethod.LOW_FREQUENCY_1_COUNTER,
        )
        ch.ci_freq_term = src
        task.timing.cfg_implicit_timing(
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=2,   # LOW_FREQUENCY_1_COUNTER needs buffer >= 2
        )
        task.start()
        freq = task.read(number_of_samples_per_channel=1, timeout=meas_time + 5.0)
        if isinstance(freq, list):
            freq = freq[0]

    print(f"[pfi] Frequency on PFI{pfi_line}: {freq:.4f} Hz")
    return float(freq)


# ── AI external trigger via PFI ───────────────────────────────

def arm_ai_trigger(
    task: nidaqmx.Task,
    pfi_line: int = 0,
    edge: str = "rising",
    device: str = DEVICE,
) -> None:
    """
    Configure an already-set-up AI task to wait for a hardware
    trigger on a PFI line before starting acquisition.

    Call this AFTER adding channels and timing to the task,
    but BEFORE calling task.start().

    Args:
        task:      an nidaqmx.Task with AI channels already configured
        pfi_line:  PFI line number to use as trigger source (0–15)
        edge:      "rising" (default) or "falling"
        device:    DAQ device name

    Example:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan("Dev2/ai0")
            task.timing.cfg_samp_clk_timing(rate=10000,
                sample_mode=AcquisitionType.FINITE, samps_per_chan=1000)
            arm_ai_trigger(task, pfi_line=0)   # wait for rising edge on PFI0
            task.start()
            data = task.read(number_of_samples_per_channel=1000)
    """
    edge_const = Edge.RISING if edge == "rising" else Edge.FALLING
    src = f"/{device}/PFI{pfi_line}"
    task.triggers.start_trigger.cfg_dig_edge_start_trig(src, trigger_edge=edge_const)
    print(f"[pfi] AI trigger armed: PFI{pfi_line} {edge} edge")


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    import nidaqmx
    from nidaqmx.constants import AcquisitionType

    print("=== PFI self-test ===")
    print("Generating 10 kHz on ctr0 (PFI12) for 0.5s...")
    t = generate_pulse(frequency=10_000)
    time.sleep(0.5)
    stop_pulse(t)

    print("\nTo test count_edges / measure_frequency:")
    print("  Wire PFI12 → PFI0, then run:")
    print("  count_edges(duration=1.0, pfi_line=0)")
    print("  measure_frequency(pfi_line=0)")