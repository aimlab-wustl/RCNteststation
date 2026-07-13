# ============================================================
# hardware/cdc_serial.py — USB CDC Serial Transport Layer
# AIMLAB_TESTSTATION_ADC_V1
#
# Thin wrapper around pyserial for COM4 (STM32 USB CDC).
# Used by stm_adc.py and stm_dio.py — not called directly.
#
# All commands are ASCII + \n.
# All responses end with \r\n.
# Response prefix:  OK:...  |  ERR:...  |  DATA:...
# ============================================================

import serial
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import STM_COM_PORT, STM_BAUD_RATE, STM_TIMEOUT

# ── Module-level singleton port ──────────────────────────────
_port: serial.Serial = None


def open_port(port: str = STM_COM_PORT,
              baud: int = STM_BAUD_RATE,
              timeout: float = STM_TIMEOUT) -> serial.Serial:
    """
    Open the CDC serial port. Returns the port object.
    Safe to call multiple times — returns existing port if already open.
    """
    global _port
    if _port is not None and _port.is_open:
        return _port
    _port = serial.Serial(port, baudrate=baud, timeout=timeout)
    time.sleep(0.1)      # brief settle after open
    _port.reset_input_buffer()
    return _port


def close_port():
    """Close the CDC port."""
    global _port
    if _port and _port.is_open:
        _port.close()
    _port = None


def send_command(cmd: str, port: serial.Serial = None) -> str:
    """
    Send one ASCII command and return the first meaningful response line.

    Args:
        cmd:  Command string WITHOUT trailing newline.
        port: Serial port object, or None to use module singleton.

    Returns:
        Response string (stripped), e.g. "OK:AIMLAB_..." or "ERR:..."

    Raises:
        RuntimeError if port not open or timeout.
    """
    p = port or _port
    if p is None or not p.is_open:
        raise RuntimeError("CDC port not open — call open_port() first")

    p.reset_input_buffer()
    p.write((cmd.strip() + '\n').encode('ascii'))
    p.flush()

    # Read lines until we get one that starts with OK:, ERR:, or DATA:
    # Skips blank lines and stray \r\n that USB CDC sometimes emits
    deadline = time.time() + (p.timeout or 2.0)
    while time.time() < deadline:
        raw = p.readline()
        if not raw:
            raise RuntimeError(f"Timeout waiting for response to '{cmd}'")
        line = raw.decode('ascii', errors='replace').strip().rstrip('\r\n')
        if not line:
            continue   # skip blank lines
        # Debug — uncomment if you need to see raw responses:
        # print(f"[CDC raw] '{line}'")
        if line.startswith(('OK:', 'ERR:', 'DATA:')):
            return line
        # Got something unexpected — return it anyway so caller can handle
        return line

    raise RuntimeError(f"Timeout waiting for response to '{cmd}'")


def send_command_multi(cmd: str,
                       terminator: str = None,
                       timeout_s: float = 10.0,
                       port: serial.Serial = None) -> list:
    """
    Send one command and collect multiple response lines.
    Stops when:
      - A line starting with 'OK:' or 'ERR:' is received (and terminator=None)
      - A line equal to terminator is received
      - timeout_s elapses

    Used for STMADC_STREAM finite captures.

    Returns:
        List of response strings (stripped).
    """
    p = port or _port
    if p is None or not p.is_open:
        raise RuntimeError("CDC port not open")

    p.reset_input_buffer()
    p.write((cmd.strip() + '\n').encode('ascii'))
    p.flush()

    lines = []
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        raw = p.readline()
        if not raw:
            continue
        line = raw.decode('ascii', errors='replace').strip()
        if not line:
            continue
        lines.append(line)
        # Stop conditions
        if terminator and line == terminator:
            break
        if terminator is None:
            if line.startswith('OK:STREAM_DONE') or line.startswith('ERR:'):
                break

    return lines


def ping(port: serial.Serial = None) -> bool:
    """
    Send IDENTIFY and verify the firmware responds correctly.
    Returns True if board is alive and running expected firmware.
    """
    try:
        resp = send_command("IDENTIFY", port=port)
        return resp.startswith("OK:AIMLAB")
    except Exception:
        return False