from hardware import dac_initialize, generate_sine, stop_sine
import time

# dac_initialize()
task = generate_sine(1, 1, frequency=20, amplitude=2.0, offset=2.5)
# DAC1 CH1 now outputs a 20 Hz sine, ±2V around 2.5V
# Your oscilloscope will show it
time.sleep(30)
stop_sine()