# ============================================================
# hardware/stm_dio.py — STM32 Digital I/O  (PD0–PD15)
# AIMLAB_TESTSTATION_ADC_V1
#
# Controls STM32H743 digital I/O lines via USB CDC commands.
#
# Pin mapping:
#   PD0–PD7   : fixed outputs (write only)
#   PD8–PD9   : configurable direction (read or write)
#   PD12–PD15 : fixed outputs (write only, formerly PWM)
#
# API:
#   STMDIO class — full OOP interface
#   Module-level functions — quick access without instantiation
#
# Usage:
#   from hardware.stm_dio import STMDIO
#   dio = STMDIO()
#   dio.write(3, 1)           # set PD3 high
#   dio.write_mask(0x00FF)    # write all 8 lower pins
#   v = dio.read(8)           # read PD8 state
#   state = dio.read_all()    # returns dict {0:0, 1:0, ..., 9:0}
#   dio.set_direction(8, "IN")
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hardware.cdc_serial import open_port, send_command, ping
from config import STM_COM_PORT, STM_BAUD_RATE, STM_TIMEOUT


class STMDIO:
    """
    STM32 Digital I/O interface over USB CDC.

    Wraps DIO_Write(), DIO_Read(), DIO_SetDirection(),
    DIO_WritePWM() from dio.c via cmd_parser commands.
    """

    # Readable pins (PD0-PD9, PD12-PD15)
    READABLE_PINS  = list(range(10)) + [12, 13, 14, 15]
    # Writable pins (PD0-PD9, PD12-PD15)
    WRITABLE_PINS  = list(range(10)) + [12, 13, 14, 15]
    # Direction-switchable (PD8, PD9, PD12-PD15)
    BIDIR_PINS     = [8, 9, 12, 13, 14, 15]

    def __init__(self,
                 port: str = STM_COM_PORT,
                 baud: int = STM_BAUD_RATE,
                 timeout: float = STM_TIMEOUT):
        self._port = open_port(port, baud, timeout)
        if not ping(self._port):
            raise RuntimeError(
                f"STM32 not responding on {port}. "
                "Check cable and firmware.")
        print(f"[STMDIO] Connected on {port}")

    # ── Internal: parse OK:PD0-7=0xXX,PD8=x,... response ───
    @staticmethod
    def _parse_all_response(resp: str) -> dict:
        """
        Parse 'OK:PD0-7=0xAA,PD8=0,PD9=1,PD12=0,PD13=1,PD14=0,PD15=0'
        into {0:1, 1:0, ..., 8:0, 9:1, 12:0, 13:1, 14:0, 15:0}
        """
        if not resp.startswith("OK:"):
            raise ValueError(f"Unexpected response: '{resp}'")
        result = {}
        for part in resp[3:].split(','):
            part = part.strip()
            if '=' not in part:
                continue
            key, val = part.split('=', 1)
            key = key.strip()
            val = val.strip()
            if key == 'PD0-7':
                # hex byte — expand to individual pins
                byte = int(val, 16)
                for bit in range(8):
                    result[bit] = (byte >> bit) & 1
            elif key.startswith('PD'):
                try:
                    pin = int(key[2:])
                    result[pin] = int(val)
                except ValueError:
                    continue
        return result

    @staticmethod
    def _parse_mask(resp: str) -> int:
        """Extract hex mask from 'OK:DIO=0x00FF' → 255 (legacy single reads)"""
        if not resp.startswith("OK:"):
            raise ValueError(f"Unexpected response: '{resp}'")
        idx = resp.find("0x")
        if idx == -1:
            idx = resp.find("=")
            if idx == -1:
                raise ValueError(f"No value in response: '{resp}'")
            return int(resp[idx + 1:], 10)
        return int(resp[idx:], 16)

    @staticmethod
    def _check_ok(resp: str, context: str = ""):
        if resp.startswith("ERR:"):
            raise RuntimeError(f"Firmware error{' in ' + context if context else ''}: {resp}")

    # ── write ─────────────────────────────────────────────────
    def write(self, pin: int, state: int):
        """
        Set a single DIO pin high (1) or low (0).

        Args:
            pin:   0-9 (PD0-PD9) or 12-15 (PD12-PD15)
            state: 0 or 1

        Example:
            dio.write(3, 1)    # PD3 high
            dio.write(12, 0)   # PD12 low
        """
        if pin not in self.WRITABLE_PINS:
            raise ValueError(f"Pin {pin} not writable. "
                             f"Valid: {self.WRITABLE_PINS}")
        state = 1 if state else 0
        resp = send_command(f"STMDIO_WRITE_PIN {pin} {state}",
                            port=self._port)
        self._check_ok(resp, f"write(pin={pin})")

    # ── write_mask ────────────────────────────────────────────
    def write_mask(self, mask: int):
        """
        Write all 8 lower DIO pins (PD0-PD7) at once.

        Args:
            mask: integer bitmask, bit N controls PD-N.
                  e.g. 0xFF = all high, 0x01 = only PD0 high

        Example:
            dio.write_mask(0b00001111)   # PD0-PD3 high, PD4-PD7 low
            dio.write_mask(0x00FF)       # all 8 pins high
        """
        mask = int(mask) & 0xFFFF
        resp = send_command(f"STMDIO_WRITE 0x{mask:04X}", port=self._port)
        self._check_ok(resp, "write_mask")
        return self._parse_mask(resp)

    # ── read ──────────────────────────────────────────────────
    def read(self, pin: int) -> int:
        """
        Read a single DIO pin state.

        Args:
            pin: 0-9 (PD0-PD9)

        Returns:
            0 or 1

        Example:
            state = dio.read(8)    # read PD8
        """
        if pin not in self.READABLE_PINS:
            raise ValueError(f"Pin {pin} not readable. "
                             f"Valid: {self.READABLE_PINS}")
        resp = send_command(f"STMDIO_READ_PIN {pin}", port=self._port)
        self._check_ok(resp, f"read(pin={pin})")
        # Response: OK:PIN8=1
        eq = resp.rfind('=')
        if eq == -1:
            raise ValueError(f"Cannot parse pin state from: '{resp}'")
        return int(resp[eq + 1:])

    # ── read_all ──────────────────────────────────────────────
    def read_all(self) -> dict:
        """
        Read all readable DIO pins (PD0-PD9, PD12-PD15) at once.

        Returns:
            dict {pin_number: state}
            e.g. {0:0, 1:1, ..., 9:0, 12:0, 13:1, 14:0, 15:0}

        Example:
            state = dio.read_all()
            if state[12]:
                print("PD12 is high")
        """
        resp = send_command("STMDIO_READ", port=self._port)
        self._check_ok(resp, "read_all")
        return self._parse_all_response(resp)

    # ── read_mask ─────────────────────────────────────────────
    def read_mask(self) -> int:
        """
        Read all DIO pins and return as integer bitmask.
        Bit N = state of PD-N.

        Returns:
            int, e.g. 0x0055
            Bits 0-7  = PD0-PD7
            Bits 8-9  = PD8-PD9
            Bits 12-15 = PD12-PD15

        Example:
            mask = dio.read_mask()
            print(f"DIO state: 0x{mask:04X}")
        """
        resp = send_command("STMDIO_READ", port=self._port)
        self._check_ok(resp, "read_mask")
        state = self._parse_all_response(resp)
        mask = 0
        for pin, val in state.items():
            mask |= (val << pin)
        return mask

    # ── set_direction ─────────────────────────────────────────
    def set_direction(self, pin: int, direction: str):
        """
        Set direction for a bidirectional pin.
        Supported pins: 8, 9, 12, 13, 14, 15

        Args:
            pin:       8, 9, 12, 13, 14, or 15
            direction: "IN" or "OUT"

        Example:
            dio.set_direction(12, "IN")
            state = dio.read(12)
            dio.set_direction(12, "OUT")
            dio.write(12, 1)
        """
        if pin not in self.BIDIR_PINS:
            raise ValueError(f"Only pins {self.BIDIR_PINS} support direction change")
        direction = direction.upper()
        if direction not in ("IN", "OUT"):
            raise ValueError("Direction must be 'IN' or 'OUT'")
        resp = send_command(f"STMDIO_DIR {pin} {direction}",
                            port=self._port)
        self._check_ok(resp, f"set_direction(pin={pin})")
        print(f"[STMDIO] PD{pin} direction → {direction}")

    # ── pulse ─────────────────────────────────────────────────
    def pulse(self, pin: int, duration_ms: float = 10.0):
        """
        Pulse a pin high then low.

        Args:
            pin:         writable pin 0-9 or 12-15
            duration_ms: pulse width in milliseconds

        Example:
            dio.pulse(0, 5.0)   # 5ms pulse on PD0
        """
        import time
        self.write(pin, 1)
        time.sleep(duration_ms / 1000.0)
        self.write(pin, 0)

    # ── clear_all ─────────────────────────────────────────────
    def clear_all(self):
        """Set all writable DIO pins to 0 (PD0-PD7)."""
        resp = send_command("STMDIO_WRITE 0x0000", port=self._port)
        self._check_ok(resp, "clear_all")
        print("[STMDIO] All DIO pins cleared (PD0-PD7 = 0)")

    # ── print_state ───────────────────────────────────────────
    def print_state(self):
        """Print current state of all readable pins."""
        state = self.read_all()
        print("[STMDIO] Current pin states:")
        for pin in sorted(state.keys()):
            label = f"PD{pin}"
            bar   = "█" if state[pin] else "░"
            print(f"  {label:5s} [{bar}]  {state[pin]}")

    # ── selftest ──────────────────────────────────────────────
    def selftest(self):
        """
        Write a walking-ones pattern to PD0-PD7 and read back.
        Connect PD0-PD7 to PD8/PD9 externally to verify loopback.
        """
        print("[STMDIO] Self-test — walking-ones PD0–PD7:")
        self.set_direction(8, "IN")
        self.set_direction(9, "IN")
        for i in range(8):
            mask = 1 << i
            self.write_mask(mask)
            state = self.read_all()
            written = f"0x{mask:02X}"
            read_back = f"0x{sum(state[p] << p for p in range(8)):02X}"
            print(f"  Write {written}  ReadBack {read_back}")
        self.clear_all()
        print("[STMDIO] Self-test done.")


# ── Module-level convenience functions ───────────────────────

_default_dio: STMDIO = None

def _get_default() -> STMDIO:
    global _default_dio
    if _default_dio is None:
        _default_dio = STMDIO()
    return _default_dio

def write(pin: int, state: int):
    return _get_default().write(pin, state)

def write_mask(mask: int):
    return _get_default().write_mask(mask)

def read(pin: int) -> int:
    return _get_default().read(pin)

def read_all() -> dict:
    return _get_default().read_all()

def set_direction(pin: int, direction: str):
    return _get_default().set_direction(pin, direction)


# ── Quick self-test ───────────────────────────────────────────
if __name__ == "__main__":
    dio = STMDIO()
    dio.print_state()
    print("\nWriting 0xAA to PD0-PD7...")
    dio.write_mask(0xAA)
    dio.print_state()
    print("\nClearing all...")
    dio.clear_all()
    dio.print_state()