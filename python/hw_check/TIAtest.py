from hardware.tia import TIA
# tia = TIA(skip_cal=True)
# tia.calibrate()          # runs Keithley sweep, saves tia_cal.json

tia = TIA()              # loads tia_cal.json automatically

# Single reading
print(tia.read())

# Averaged
print(tia.read_avg(n=64))

# Console printout
tia.print_current()

# Stats
tia.print_stats(n=256)

# Switch range
tia.set_range('B_200K')

# Live plot
tia.live()

# Record 10 seconds
t, i = tia.record(duration=10, n_avg=8)

# Stats dict for your own code
s = tia.stats(n=128)
print(s['mean_uA'], s['std_nA'])