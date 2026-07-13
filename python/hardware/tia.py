# ============================================================
# hardware/tia.py — TIA Current Measurement Module
# AIMLAB_TESTSTATION_V3
#
# Complete self-contained module: calibration + measurement.
# Place in E:\AIM\PythonScript0321\hardware\tia.py
#
# Quick start:
#   from hardware.tia import TIA
#
#   # First time — run calibration (needs Keithley connected):
#   tia = TIA(skip_cal=True)
#   tia.calibrate()
#
#   # Every session after:
#   tia = TIA()                     # loads tia_cal.json automatically
#   tia.set_range('B_20K')
#   print(tia.read())               # single reading µA
#   print(tia.read_avg(n=64))       # averaged reading µA
#   tia.print_current()             # print to console
#   tia.print_stats(n=256)          # mean/std/min/max
#   tia.live()                      # live plot (blocking)
#   t, i = tia.record(duration=10) # capture array
#   s = tia.stats(n=128)           # stats dict
# ============================================================

import os, sys, json, time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hardware.cdc_serial import open_port, send_command
from hardware.ads131a04  import ADS131

# ── Default paths ─────────────────────────────────────────────
_HW_DIR  = os.path.dirname(os.path.abspath(__file__))
_CAL_FILE = os.path.join(_HW_DIR, '..', 'tia_cal.json')

# ── Keithley address ──────────────────────────────────────────
KEITHLEY_ADDR = 'USB0::0x05E6::0x2450::04345889::INSTR'

# ── Range definitions ─────────────────────────────────────────
# (gain_cmd, Rf_nominal, I_max_for_cal, osr)
_RANGES = {
    'B_20K':  ('TIA_GAIN B 20K',  20e3,  80e-6,  400),
    'B_200K': ('TIA_GAIN B 200K', 200e3, 8e-6,   4096),
    'B_2M':   ('TIA_GAIN B 2M',   2e6,   800e-9, 4096),
}

# ── Calibration defaults ──────────────────────────────────────
_CAL_N_POINTS = 21
_CAL_N_AVG    = 256
_CAL_SETTLE_S = 0.6


class TIA:
    """
    Calibrated TIA current measurement module.
    Wraps OPA3S328 gain select + ADS131 Chip2 CH4.

    Ranges (Amp B):
        B_20K   → ±100µA  (20kΩ  feedback)
        B_200K  → ±10µA   (200kΩ feedback)
        B_2M    → ±1µA    (2MΩ   feedback)
    """

    def __init__(self, cal_file: str = _CAL_FILE, skip_cal: bool = False):
        """
        skip_cal: set True to initialise without a calibration file.
                  Only do this before running calibrate().
        """
        self._cal      = None
        self._range    = None
        self._rf       = None
        self._voff     = None
        self._i_max    = None
        self._cal_file = os.path.abspath(cal_file)

        # Open hardware
        self._port = open_port()
        self._adc  = ADS131()

        if skip_cal:
            print('[TIA] Skipping calibration load — call calibrate() first.')
            return

        # Load calibration
        self._load_cal()
        self.set_range('B_20K')

    # ══════════════════════════════════════════════════════════
    # Calibration
    # ══════════════════════════════════════════════════════════

    def calibrate(self,
                  keithley_addr: str = KEITHLEY_ADDR,
                  n_points: int = _CAL_N_POINTS,
                  n_avg:    int = _CAL_N_AVG,
                  settle_s: float = _CAL_SETTLE_S,
                  ranges: list = None):
        """
        Run full calibration sweep with Keithley 2450.

        Connections:
            Keithley HI → -INB on board
            Keithley LO → board GND

        Saves results to tia_cal.json automatically.

        ranges: list of range labels to calibrate, default all three.
                e.g. ['B_20K', 'B_200K'] to skip 2M
        """
        import pyvisa

        if ranges is None:
            ranges = list(_RANGES.keys())

        print('\n' + '='*60)
        print('TIA CALIBRATION')
        print('='*60)
        print(f'Keithley: {keithley_addr}')
        print('Ensure: Keithley HI → -INB,  Keithley LO → board GND')
        input('Press ENTER to start...\n')

        # Open Keithley
        print(f'Connecting to Keithley...')
        rm    = pyvisa.ResourceManager()
        keith = rm.open_resource(keithley_addr)
        keith.timeout = 10000
        keith.write('*RST')
        time.sleep(1.0)
        idn = keith.query('*IDN?').strip()
        print(f'  {idn}\n')

        def _keith_setup(i_range_A):
            keith.write('*RST')
            time.sleep(0.5)
            keith.write('SOUR:FUNC CURR')
            keith.write(f'SOUR:CURR:RANG {i_range_A:.2e}')
            keith.write('SOUR:CURR:VLIM 5')
            keith.write('SENS:FUNC "VOLT"')
            keith.write('SENS:VOLT:RANG 10')
            keith.write('SENS:VOLT:NPLC 1')
            keith.write('OUTP ON')

        def _keith_set(i_A):
            keith.write(f'SOUR:CURR {i_A:.6e}')
            time.sleep(settle_s)

        def _keith_off():
            keith.write('SOUR:CURR 0')
            time.sleep(0.05)
            keith.write('OUTP OFF')

        def _read_ch4_avg(n):
            vals = [self._adc.read_frame(2)[4] for _ in range(n)]
            return float(np.mean(vals)), float(np.std(vals))

        cal_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'n_points':  n_points,
            'n_avg':     n_avg,
            'ranges':    {}
        }

        for label in ranges:
            gain_cmd, rf_nom, i_max, osr = _RANGES[label]
            print(f'── Range: {label}  Rf_nom={rf_nom/1e3:.0f}kΩ  '
                  f'I_max=±{i_max*1e6:.2f}µA ──')

            # Set gain and OSR
            send_command(gain_cmd, port=self._port)
            self._adc.set_osr(2, osr)
            time.sleep(0.2)

            # Configure Keithley
            _keith_setup(i_max)
            time.sleep(0.5)

            # Sweep
            sweep = np.linspace(-i_max, i_max, n_points)
            results = []

            print(f'  {"I_set(µA)":>12}  {"V_ch4(mV)":>10}  {"std(µV)":>8}')
            print(f'  {"-"*36}')

            for i_set in sweep:
                _keith_set(i_set)
                v_mean, v_std = _read_ch4_avg(n_avg)
                results.append((i_set, v_mean))
                print(f'  {i_set*1e6:>12.4f}  {v_mean*1000:>10.4f}  '
                      f'{v_std*1e6:>8.2f}')

            _keith_off()

            # Fit: V = slope*I + intercept  (TIA is inverting → slope < 0)
            i_arr = np.array([r[0] for r in results])
            v_arr = np.array([r[1] for r in results])
            coeffs   = np.polyfit(i_arr, v_arr, 1)
            rf_eff   = abs(coeffs[0])      # take abs — inverting TIA
            v_offset = coeffs[1]
            residual = np.std(v_arr - np.polyval(coeffs, i_arr))

            print(f'\n  Rf_nominal  = {rf_nom:.0f} Ω')
            print(f'  Rf_eff      = {rf_eff:.2f} Ω  '
                  f'({(rf_eff-rf_nom)/rf_nom*100:+.2f}%)')
            print(f'  V_offset    = {v_offset*1000:.4f} mV')
            print(f'  Residual    = {residual*1e6:.2f} µV RMS')
            print(f'  Formula     : I = -(V_ch4 - {v_offset:.6f}) / {rf_eff:.2f}\n')

            cal_data['ranges'][label] = {
                'gain_cmd':   gain_cmd,
                'rf_nominal': rf_nom,
                'rf_eff':     rf_eff,
                'v_offset':   v_offset,
                'residual_v': residual,
                'i_max':      i_max,
                'raw_i':      i_arr.tolist(),
                'raw_v':      v_arr.tolist(),
            }

        keith.close()
        rm.close()

        # Save
        with open(self._cal_file, 'w') as f:
            json.dump(cal_data, f, indent=2)

        print('='*60)
        print(f'Calibration saved → {self._cal_file}')
        print('='*60)
        self._print_cal_summary(cal_data)

        # Load into self
        self._cal = cal_data
        self.set_range('B_20K')

    def _load_cal(self):
        if not os.path.exists(self._cal_file):
            raise FileNotFoundError(
                f'No calibration file: {self._cal_file}\n'
                f'Run:  tia = TIA(skip_cal=True); tia.calibrate()'
            )
        with open(self._cal_file) as f:
            self._cal = json.load(f)
        print(f'[TIA] Calibration loaded: {self._cal["timestamp"]}')
        self._print_cal_summary(self._cal)

    def _print_cal_summary(self, cal):
        print(f'\n  {"Range":<10}  {"Rf_eff(Ω)":>12}  '
              f'{"V_offset(mV)":>14}  {"Residual(µV)":>14}  {"Noise(nA)":>10}')
        print(f'  {"-"*66}')
        for label, d in cal['ranges'].items():
            noise_nA = d['residual_v'] / d['rf_eff'] * 1e9
            print(f'  {label:<10}  {d["rf_eff"]:>12.1f}  '
                  f'{d["v_offset"]*1000:>14.4f}  '
                  f'{d["residual_v"]*1e6:>14.2f}  '
                  f'{noise_nA:>10.2f}')
        print()

    def load_cal(self, cal_file: str = None):
        """Reload calibration from file (useful after re-calibrating)."""
        if cal_file:
            self._cal_file = os.path.abspath(cal_file)
        self._load_cal()
        self.set_range(self._range or 'B_20K')

    # ══════════════════════════════════════════════════════════
    # Range selection
    # ══════════════════════════════════════════════════════════

    def set_range(self, label: str):
        """
        Select gain range: 'B_20K' | 'B_200K' | 'B_2M'
        """
        if self._cal is None:
            raise RuntimeError('No calibration loaded — run calibrate() first.')
        if label not in self._cal['ranges']:
            raise ValueError(
                f"Unknown range '{label}'. "
                f"Valid: {list(self._cal['ranges'].keys())}"
            )
        d        = self._cal['ranges'][label]
        gain_cmd = d['gain_cmd']
        _, _, _, osr = _RANGES[label]

        resp = send_command(gain_cmd, port=self._port)
        if not resp.startswith('OK'):
            raise RuntimeError(f'Gain command failed: {resp}')

        self._adc.set_osr(2, osr)
        self._range = label
        self._rf    = d['rf_eff']
        self._voff  = d['v_offset']
        self._i_max = d['i_max']

        print(f'[TIA] Range: {label}  Rf={self._rf:.0f}Ω  '
              f'±{self._i_max*1e6:.1f}µA FS  OSR={osr}')

    @property
    def range(self) -> str:
        return self._range

    @property
    def full_scale_uA(self) -> float:
        return self._i_max * 1e6

    # ══════════════════════════════════════════════════════════
    # Internal conversion
    # ══════════════════════════════════════════════════════════

    def _v_to_i(self, v: float) -> float:
        """Voltage → calibrated current µA (inverting TIA)."""
        return -((v - self._voff) / self._rf) * 1e6

    # ══════════════════════════════════════════════════════════
    # Single readings
    # ══════════════════════════════════════════════════════════

    def read_voltage(self) -> float:
        """Raw ADS131 CH4 voltage in V (OUTB − REGREF)."""
        return self._adc.read_frame(2)[4]

    def read(self) -> float:
        """Single calibrated current reading in µA."""
        return self._v_to_i(self.read_voltage())

    def read_avg(self, n: int = 64) -> float:
        """Average n frames, return calibrated current in µA."""
        vals = [self.read_voltage() for _ in range(n)]
        return self._v_to_i(float(np.mean(vals)))

    def read_frame(self) -> dict:
        """
        Single reading with metadata.
        Returns dict: current_uA, voltage_V, range, rf_eff, timestamp
        """
        v = self.read_voltage()
        return {
            'current_uA': self._v_to_i(v),
            'voltage_V':  v,
            'range':      self._range,
            'rf_eff':     self._rf,
            'timestamp':  time.time(),
        }

    def print_current(self, n: int = 32):
        """Print single averaged reading."""
        i = self.read_avg(n)
        print(f'[TIA] {self._range}  I = {i:.4f} µA  ({i*1000:.3f} nA)')

    # ══════════════════════════════════════════════════════════
    # Multi-sample
    # ══════════════════════════════════════════════════════════

    def stats(self, n: int = 256) -> dict:
        """
        Collect n readings, return stats dict.
        Keys: mean_uA, std_nA, min_uA, max_uA, n, range
        """
        vals = [self._v_to_i(self.read_voltage()) for _ in range(n)]
        arr  = np.array(vals)
        return {
            'mean_uA': float(arr.mean()),
            'std_nA':  float(arr.std() * 1000),
            'min_uA':  float(arr.min()),
            'max_uA':  float(arr.max()),
            'n':       n,
            'range':   self._range,
        }

    def print_stats(self, n: int = 256):
        """Print stats from n readings."""
        s = self.stats(n)
        print(f'[TIA] Stats ({s["range"]}, n={s["n"]}):')
        print(f'  mean = {s["mean_uA"]:>10.4f} µA')
        print(f'  std  = {s["std_nA"]:>10.3f} nA')
        print(f'  min  = {s["min_uA"]:>10.4f} µA')
        print(f'  max  = {s["max_uA"]:>10.4f} µA')

    def record(self, duration: float = 10.0, n_avg: int = 1) -> tuple:
        """
        Record current for duration seconds.

        Args:
            duration: seconds to record
            n_avg:    frames averaged per sample

        Returns:
            (times, currents) — numpy arrays in seconds and µA
        """
        print(f'[TIA] Recording {duration}s on {self._range}...')
        times, currents = [], []
        t0 = time.time()

        while time.time() - t0 < duration:
            vals = [self.read_voltage() for _ in range(max(1, n_avg))]
            times.append(time.time() - t0)
            currents.append(self._v_to_i(float(np.mean(vals))))

        t_arr = np.array(times)
        i_arr = np.array(currents)
        print(f'[TIA] Done. n={len(i_arr)}  '
              f'mean={i_arr.mean():.4f}µA  '
              f'std={i_arr.std()*1000:.3f}nA')
        return t_arr, i_arr

    # ══════════════════════════════════════════════════════════
    # Live plot
    # ══════════════════════════════════════════════════════════

    def live(self, window: int = 200, n_avg: int = 8,
             interval_ms: int = 100):
        """
        Live scrolling current plot. Blocks until window closed.

        Args:
            window:      number of points shown on plot
            n_avg:       frames averaged per plot point
            interval_ms: plot refresh interval
        """
        times, currents = [], []
        t0       = time.time()
        noise_nA = (self._cal['ranges'][self._range]['residual_v']
                    / self._rf * 1e9)

        fig, ax = plt.subplots(figsize=(11, 5))
        fig.patch.set_facecolor('#0d0d1a')
        ax.set_facecolor('#111122')
        ax.set_xlabel('Time (s)', color='#aaaacc')
        ax.set_ylabel('Current (µA)', color='#aaaacc')
        ax.set_title(
            f'TIA Live — {self._range}   Rf={self._rf:.0f}Ω   '
            f'±{self._i_max*1e6:.1f}µA FS   noise~{noise_nA:.1f}nA',
            color='#ccccee'
        )
        ax.tick_params(colors='#aaaacc')
        ax.axhline(0, color='#444466', linewidth=0.8, linestyle='--')
        ax.grid(True, color='#1a1a3a', linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_edgecolor('#333355')

        line,      = ax.plot([], [], color='#00ffcc', linewidth=0.8)
        mean_line, = ax.plot([], [], color='#ff6644', linewidth=1.2,
                             linestyle='--', label='mean')
        stats_txt  = ax.text(0.01, 0.97, '', transform=ax.transAxes,
                             color='#aaaacc', fontsize=8, va='top',
                             family='monospace')
        ax.legend(loc='upper right', facecolor='#1a1a2a',
                  labelcolor='#aaaacc', fontsize=8)

        def _update(_):
            try:
                vals = [self.read_voltage() for _ in range(n_avg)]
                i_ua = self._v_to_i(float(np.mean(vals)))
                times.append(time.time() - t0)
                currents.append(i_ua)

                t_arr  = np.array(times[-window:])
                i_arr  = np.array(currents[-window:])
                i_mean = i_arr.mean()

                line.set_data(t_arr, i_arr)
                mean_line.set_data([t_arr[0], t_arr[-1]],
                                   [i_mean, i_mean])
                ax.set_xlim(t_arr[0], t_arr[-1] + 0.1)
                span = max(abs(i_arr.max()), abs(i_arr.min()),
                           self._i_max * 1e6 * 0.05)
                ax.set_ylim(-span * 1.3, span * 1.3)

                stats_txt.set_text(
                    f'mean  = {i_mean:>10.4f} µA\n'
                    f'std   = {i_arr.std()*1000:>10.3f} nA\n'
                    f'min   = {i_arr.min():>10.4f} µA\n'
                    f'max   = {i_arr.max():>10.4f} µA\n'
                    f'n     = {len(times):>10d}'
                )
            except Exception as e:
                print(f'[TIA] read error: {e}')

        ani = animation.FuncAnimation(fig, _update,
                                      interval=interval_ms,
                                      cache_frame_data=False)
        plt.tight_layout()
        plt.show()

        if currents:
            arr = np.array(currents)
            print(f'\n[TIA] Session ended. n={len(arr)}  '
                  f'mean={arr.mean():.4f}µA  '
                  f'std={arr.std()*1000:.3f}nA')