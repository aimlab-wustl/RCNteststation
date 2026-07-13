import numpy as np
import matplotlib.pyplot as plt
import sys

# Usage:
# python plot_adc_npz.py your_capture.npz

path = sys.argv[1] if len(sys.argv) > 1 else "ads131_30s_ch1_precise.npz"

data = np.load(path, allow_pickle=True)

print("Keys in npz:")
for k in data.files:
    arr = data[k]
    print(f"  {k}: shape={getattr(arr, 'shape', None)}, dtype={getattr(arr, 'dtype', None)}")

# Try common names first
if "raw" in data.files:
    raw = data["raw"]
elif "adc" in data.files:
    raw = data["adc"]
elif "samples" in data.files:
    raw = data["samples"]
else:
    # fallback: first 1D numeric array
    raw = None
    for k in data.files:
        arr = data[k]
        if isinstance(arr, np.ndarray) and arr.ndim == 1 and np.issubdtype(arr.dtype, np.number):
            raw = arr
            print(f"Using array: {k}")
            break
    if raw is None:
        raise ValueError("No 1D numeric ADC array found in npz.")

raw = np.asarray(raw)

# Try to get rate_hz if saved
if "rate_hz" in data.files:
    rate_hz = float(data["rate_hz"])
    t = np.arange(len(raw)) / rate_hz
    x = t * 1000  # ms
    xlabel = "Time (ms)"
else:
    x = np.arange(len(raw))
    xlabel = "Sample index"

plt.figure()
plt.plot(x, raw, marker=".", markersize=2, linewidth=0.8)
plt.xlabel(xlabel)
plt.ylabel("ADC raw code")
plt.title(f"ADC capture: {path}")
plt.grid(True)

print("\nInteractive controls:")
print("  Zoom: magnifying glass icon")
print("  Pan: hand icon")
print("  Reset: home icon")
print("  You can also drag-select zoom depending on backend.")

plt.show()