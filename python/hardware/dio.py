# ============================================================
# hardware/dio.py — Digital I/O
# Covers:
#   • set_line()      — write HIGH/LOW to one digital output line
#   • get_line()      — read one digital input line
#   • set_port()      — write a list of booleans to multiple lines at once
#   • get_port()      — read multiple lines at once
#
# Note: nidaqmx requires a separate Task per direction (in vs out).
# Use DIOOutputSession when an output must stay actively driven while
# other code reads or waits.
# Each function opens and closes its own Task — simple and safe.
# For SPI bit-banging (DAC), dac.py will manage its own persistent tasks.
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import nidaqmx
from nidaqmx.constants import LineGrouping
from config import DEVICE, DIO_PORT


def _line_str(line: int, device: str = DEVICE) -> str:
    return f"{device}/{DIO_PORT}/line{line}"


def _lines_str(lines: list[int], device: str = DEVICE) -> str:
    # e.g. "Dev2/port0/line2:5"  if contiguous, else comma-separated
    if _is_contiguous(lines):
        lo, hi = min(lines), max(lines)
        if lo == hi:
            return _line_str(lo, device)
        return f"{device}/{DIO_PORT}/line{lo}:{hi}"
    return ",".join(_line_str(l, device) for l in lines)


def _normalize_lines(lines) -> list[int]:
    if isinstance(lines, int):
        lines = [lines]
    else:
        lines = list(lines)
    if not lines:
        raise ValueError("at least one DIO line is required")
    if len(set(lines)) != len(lines):
        raise ValueError(f"DIO lines must be unique, got {lines}")
    return lines


def _normalize_values(values, expected_len: int) -> list[bool]:
    if isinstance(values, bool):
        values = [values]
    else:
        values = [bool(v) for v in values]
    if len(values) != expected_len:
        raise ValueError(
            f"Expected {expected_len} DIO values, got {len(values)}"
        )
    return values


def _is_contiguous(lines: list[int]) -> bool:
    ordered = sorted(lines)
    return ordered == list(range(ordered[0], ordered[-1] + 1))


def _use_port_style(lines: list[int]) -> bool:
    return len(lines) > 1 and _is_contiguous(lines)


def _packed_value(lines: list[int], values: list[bool]) -> tuple[int, int, int]:
    """Pack values into the integer format used by CHAN_FOR_ALL_LINES."""
    lo, hi = min(lines), max(lines)
    word = 0
    for line, value in zip(lines, values):
        if value:
            word |= 1 << (line - lo)
    return word, lo, hi


def _unpack_value(word, lines: list[int]) -> list[bool]:
    lo = min(lines)
    if isinstance(word, list):
        word = word[0]
    word = int(word)
    return [bool(word & (1 << (line - lo))) for line in lines]


class DIOOutputSession:
    """
    Hold one or more DIO output lines actively driven while the context is open.

    This matters for loopback tests and enable/chip-select lines on USB DAQ
    devices: clearing the DAQmx task can release the line, so an input wired to
    it may read a pull-up/pull-down instead of the last value written.
    """

    def __init__(self, lines, initial_values=None, device: str = DEVICE):
        self.lines = _normalize_lines(lines)
        self.device = device
        if initial_values is None:
            initial_values = [False] * len(self.lines)
        self.values = _normalize_values(initial_values, len(self.lines))
        self._task = None
        self._port_style = _use_port_style(self.lines)

    def __enter__(self):
        self._task = nidaqmx.Task()
        grouping = (
            LineGrouping.CHAN_FOR_ALL_LINES
            if self._port_style
            else LineGrouping.CHAN_PER_LINE
        )
        self._task.do_channels.add_do_chan(
            _lines_str(self.lines, self.device),
            line_grouping=grouping,
        )
        self.write(self.values)
        return self

    def __exit__(self, *_):
        try:
            self.close()
        except Exception:
            pass

    def write(self, values) -> None:
        if self._task is None:
            raise RuntimeError("DIOOutputSession must be used as a context manager")
        self.values = _normalize_values(values, len(self.lines))
        if self._port_style:
            word, _, _ = _packed_value(self.lines, self.values)
            self._task.write(word)
        else:
            self._task.write(self.values[0] if len(self.values) == 1 else self.values)

    def set_line(self, line: int, value: bool) -> None:
        if line not in self.lines:
            raise ValueError(f"line {line} is not part of this DIOOutputSession")
        idx = self.lines.index(line)
        next_values = list(self.values)
        next_values[idx] = bool(value)
        self.write(next_values)

    def close(self) -> None:
        if self._task is not None:
            self._task.stop()
            self._task.close()
            self._task = None


def loopback_line(
    output_line: int,
    input_line: int,
    states: list[bool] | None = None,
    settle_s: float = 0.025,
    reads_per_state: int = 5,
    device: str = DEVICE,
) -> list[bool]:
    """
    Drive one output line and read one input line while the output task stays open.

    Returns one boolean result per requested state.
    """
    if states is None:
        states = [True, False, True, False]
    results = []
    with DIOOutputSession(output_line, initial_values=[False], device=device) as out:
        time.sleep(settle_s)
        _ = get_line(input_line, device=device)
        for state in states:
            out.write([state])
            time.sleep(settle_s)
            votes = [get_line(input_line, device=device) for _ in range(reads_per_state)]
            results.append(sum(votes) > (reads_per_state // 2))
        out.write([False])
    return results


# ── Single line ───────────────────────────────────────────────

def set_line(line: int, value: bool, device: str = DEVICE) -> None:
    """
    Set one digital output line HIGH (True) or LOW (False).

    Args:
        line:  line index, e.g. 4 → port0/line4
        value: True = HIGH, False = LOW
        device: DAQ device name

    Example:
        set_line(4, True)   # SYNC HIGH
        set_line(3, False)  # SCK LOW
    """
    set_port([line], [value], device=device)


def get_line(line: int, device: str = DEVICE) -> bool:
    """
    Read one digital input line.

    Returns:
        True if HIGH, False if LOW.

    Example:
        state = get_line(6)
    """
    return get_port([line], device=device)[0]


# ── Multiple lines ────────────────────────────────────────────

def set_port(lines: list[int], values: list[bool], device: str = DEVICE) -> None:
    """
    Write multiple digital output lines at once.

    Args:
        lines:  list of line indices
        values: list of bool values, same length as lines
        device: DAQ device name

    Example:
        set_port([1, 2, 3, 4], [True, False, False, True])
    """
    lines = _normalize_lines(lines)
    values = _normalize_values(values, len(lines))

    with nidaqmx.Task() as task:
        port_style = _use_port_style(lines)
        task.do_channels.add_do_chan(
            _lines_str(lines, device),
            line_grouping=(
                LineGrouping.CHAN_FOR_ALL_LINES
                if port_style
                else LineGrouping.CHAN_PER_LINE
            ),
        )
        if port_style:
            word, _, _ = _packed_value(lines, values)
            task.write(word)
        else:
            task.write(values[0] if len(values) == 1 else values)


def get_port(lines: list[int], device: str = DEVICE) -> list[bool]:
    """
    Read multiple digital input lines at once.

    Returns:
        List of bool values in the same order as lines.

    Example:
        states = get_port([6, 7])
    """
    lines = _normalize_lines(lines)
    with nidaqmx.Task() as task:
        port_style = _use_port_style(lines)
        task.di_channels.add_di_chan(
            _lines_str(lines, device),
            line_grouping=(
                LineGrouping.CHAN_FOR_ALL_LINES
                if port_style
                else LineGrouping.CHAN_PER_LINE
            ),
        )
        result = task.read()
        if port_style:
            return _unpack_value(result, lines)
        return [bool(v) for v in result] if isinstance(result, list) else [bool(result)]


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    print("Setting line 0 HIGH...")
    set_line(0, True)
    print("Setting line 0 LOW...")
    set_line(0, False)
    print("Reading line 6:", get_line(6))
