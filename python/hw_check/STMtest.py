'''
from hardware.stm_dio import STMDIO
dio = STMDIO()

# Write
dio.write(3, 1)             # PD3 high
dio.write(3, 0)             # PD3 low
dio.write_mask(0xFF)        # PD0-PD7 all high
dio.write_mask(0b10101010)  # alternating
dio.write_mask(0x00)        # all low

# Read
dio.set_direction(8, "OUT")
dio.set_direction(8, "IN")
state = dio.read(8)         # single pin, returns 0 or 1
state = dio.read_all()      # dict {0:0, 1:1, ..., 9:0}
print(state)                 # e.g. {0: 1, 1: 0, 2: 1, 3: 0, 4: 1, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0}
mask  = dio.read_mask()     # integer e.g. 0x00FF

# Direction (PD8, PD9 only)

# Utilities
dio.pulse(0, 1000.0)          # 10ms pulse on PD0
dio.clear_all()             # PD0-PD7 all low
dio.print_state()           # pretty print all pins
dio.selftest()              # walking-ones pattern

from hardware.cdc_serial import open_port, send_command
p = open_port()

send_command("DAC_SET 1 1 2.500", port=p)   # chip1, ch1, 2.5V
send_command("DAC_SET 1 2 4.000", port=p)   # chip1, ch2, 0V
send_command("DAC_SET_ALL 1.650", port=p)   # all chips all ch, 1.65V
'''

from hardware.stm_adc import STMADC
adc = STMADC()

# Single read
v = adc.read_single(1)          # one float, PA1
v = adc.read_single(2)          # PA2
v = adc.read_single("ALL")      # dict {1: V, 2: V, 3: V, 4: V}

# Buffered finite capture
v, t = adc.read_buffered(1, 100)    # 100 samples from PA1
v, t = adc.read_buffered(2, 500)    # 500 samples from PA2

# Live oscilloscope plot (blocks until window closed)
adc.read_continuous(1)                          # PA1, indefinite
adc.read_continuous(1, duration=10)             # PA1, 10 seconds
adc.read_continuous(1, window_sec=5.0)          # wider time window
adc.read_continuous(1, csv_filename="out.csv")  # save to CSV

# Quick 4-channel health check
adc.selftest()
