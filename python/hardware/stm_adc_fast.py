"""
hardware/stm_adc_fast.py
=========================
Python control for the ADCFAST_CAPTURE firmware command (TIM1/TRGO2 +
DMA2_Stream0 + ADC1/PA1 burst capture -- see adc_capture.c/.h).

Uses the same CDC serial singleton as ads131a04.py/tia.py -- safe to
call alongside those, no separate port needed.

Protocol (binary transfer -- NOT the original 20-line ASCII CSV
version, which measured ~10.2s round trip for 1000 samples, over
100x slower than the ~100ms capture itself):
    host  -> ADCFAST_CAPTURE n_samples prescaler period
    board -> BINARY:<n_bytes>          (text line)
             <n_bytes of raw data>      (binary, NOT line-based)
             OK:ADCFAST_DONE n=<n>      (text line)
    or      ERR:...                    (text line, on failure)

Raw codes are 16-bit, single-ended, 0..65535 over 0..3.3V -- same
convention as ADC_ReadVoltage() in dio.c/.h.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time as _time
import numpy as np
from hardware import cdc_serial

TIM1_CLOCK_HZ = 240e6   # ASSUMED -- confirmed for TIM6/APB1 (HSE=8MHz ->
                        # PLL1=480MHz -> AHB/DIV2=240MHz -> APB1/DIV2=120MHz
                        # -> 2x doubling = 240MHz), but TIM1 is on APB2,
                        # whose divider hasn't been independently confirmed.
                        # Cross-check against ADCFAST_DBG's elapsed_ms
                        # before trusting this for anything precision-critical.
ADCFAST_MAX_SAMPLES = 8000   # must match adc_capture.h
VREF_ONBOARD = 3.3            # onboard ADC reference, matches ADC_ReadVoltage()


def _prescaler_period_for_rate(rate_hz: float) -> tuple[int, int, float]:
    """
    Pick (prescaler, period) achieving rate_hz as closely as possible.
    Returns (prescaler, period, actual_achieved_rate_hz).

    Single-divisor only (prescaler=0, period=divisor-1) -- covers
    ~3.66kSPS up to 3.2MSPS, which is the whole range this project
    needs so far. Raises for anything slower than that; specify
    prescaler/period manually via capture() for such cases.
    """
    total_div = TIM1_CLOCK_HZ / rate_hz
    total_div_int = round(total_div)
    if total_div_int < 1:
        raise ValueError(
            f"{rate_hz/1e6:.3f} MSPS exceeds TIM1/ADC capability "
            f"(ceiling ~3.2 MSPS with current ADC clock config)"
        )
    if total_div_int > 65536:
        raise ValueError(
            f"{rate_hz:.1f} Hz is below the single-divisor floor "
            f"(~{TIM1_CLOCK_HZ/65536:.0f} Hz) -- call capture() directly "
            f"with an explicit prescaler/period pair instead"
        )
    period = total_div_int - 1
    actual_rate = TIM1_CLOCK_HZ / (period + 1)
    return 0, period, actual_rate


def capture(n_samples: int, prescaler: int, period: int,
            timeout_s: float = 10.0) -> dict:
    """
    Run one burst capture and return the result.

    Returns dict with:
        raw       -- np.ndarray of uint16 raw ADC codes
        voltage   -- np.ndarray of float volts (0..3.3V)
        n         -- number of samples actually returned
        rate_hz   -- ASSUMED sample rate (from prescaler/period clock
                     math -- NOT measured; cross-check against
                     ADCFAST_DBG's elapsed_ms before trusting it)
        round_trip_s -- actual wall-clock time for the whole exchange
    """
    if n_samples > ADCFAST_MAX_SAMPLES:
        raise ValueError(f"n_samples max is {ADCFAST_MAX_SAMPLES}")

    port = cdc_serial.open_port()
    cmd = f"ADCFAST_CAPTURE {n_samples} {prescaler} {period}"

    t0 = _time.time()
    port.reset_input_buffer()
    port.write((cmd.strip() + "\n").encode("ascii"))
    port.flush()

    header = port.readline().decode("ascii", errors="replace").strip()
    if header.startswith("ERR:"):
        raise RuntimeError(f"ADCFAST_CAPTURE failed: {header}")
    if not header.startswith("BINARY:"):
        raise RuntimeError(f"unexpected response (expected BINARY:...): {header!r}")
    n_bytes = int(header[len("BINARY:"):])

    payload = port.read(n_bytes)   # raw byte read, NOT line-based --
                                    # binary data can contain bytes that
                                    # look like newlines
    if len(payload) != n_bytes:
        raise RuntimeError(f"expected {n_bytes} bytes, got {len(payload)} "
                            f"-- check port timeout vs actual transfer time")

    ok_line = port.readline().decode("ascii", errors="replace").strip()
    if not ok_line.startswith("OK:"):
        raise RuntimeError(f"expected OK: line after payload, got {ok_line!r}")

    round_trip_s = _time.time() - t0

    raw = np.frombuffer(payload, dtype="<u2")   # little-endian uint16,
                                                  # matches Cortex-M7 default
    if len(raw) != n_samples:
        raise RuntimeError(
            f"expected {n_samples} samples, decoded {len(raw)} from payload"
        )

    voltage = raw.astype(np.float64) / 65535.0 * VREF_ONBOARD
    rate_hz = TIM1_CLOCK_HZ / (prescaler + 1) / (period + 1)

    return {"raw": raw, "voltage": voltage, "n": len(raw), "rate_hz": rate_hz,
            "round_trip_s": round_trip_s}


def capture_at_rate(n_samples: int, rate_hz: float, timeout_s: float = 10.0) -> dict:
    """Convenience wrapper: specify a target sample rate directly instead
    of prescaler/period. Result dict's 'rate_hz' is the ASSUMED achieved
    rate (integer divisor rounding on the clock-math assumption), not
    independently measured -- see ADCFAST_DBG's elapsed_ms for that."""
    prescaler, period, actual_rate = _prescaler_period_for_rate(rate_hz)
    result = capture(n_samples, prescaler, period, timeout_s=timeout_s)
    if abs(actual_rate - result["rate_hz"]) > 1e-3:
        # sanity check -- should never actually fire, but if the firmware
        # and this module's clock-math assumptions ever drift apart,
        # better to know loudly than silently trust the wrong number
        raise RuntimeError(
            f"rate mismatch: computed {actual_rate:.1f}Hz vs "
            f"result {result['rate_hz']:.1f}Hz -- TIM1 clock assumption "
            f"(240MHz) may be wrong, verify before trusting timing data"
        )
    return result


if __name__ == "__main__":
    print("Quick sanity check: 1000 samples @ 10kSPS")
    r = capture_at_rate(1000, 10_000)
    print(f"  n={r['n']}  rate={r['rate_hz']:.1f}Hz (assumed, from clock math)")
    print(f"  round trip: {r['round_trip_s']*1000:.1f}ms total "
          f"(expected capture-only time: {r['n']/r['rate_hz']*1000:.1f}ms -- "
          f"any remaining gap is real overhead worth chasing further)")
    print(f"  raw:     min={r['raw'].min()}  max={r['raw'].max()}  "
          f"mean={r['raw'].mean():.1f}  std={r['raw'].std():.1f}")
    print(f"  voltage: min={r['voltage'].min():.4f}V  max={r['voltage'].max():.4f}V  "
          f"mean={r['voltage'].mean():.4f}V")