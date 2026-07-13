# import numpy as np
# import matplotlib.pyplot as plt
# import sys
# from pathlib import Path

# # Usage:
# # python plot_adc_npz.py your_capture.npz

# path = sys.argv[1] if len(sys.argv) > 1 else "ads131_30s_ch1.npz"

# data = np.load(path, allow_pickle=True)

# print("Keys in npz:")
# for k in data.files:
#     arr = data[k]
#     print(
#         f"  {k}: shape={getattr(arr, 'shape', None)}, "
#         f"dtype={getattr(arr, 'dtype', None)}"
#     )

# # Find ADC samples
# if "raw" in data.files:
#     raw = data["raw"]
# elif "adc" in data.files:
#     raw = data["adc"]
# elif "samples" in data.files:
#     raw = data["samples"]
# else:
#     raw = None

#     for k in data.files:
#         arr = data[k]

#         if (
#             isinstance(arr, np.ndarray)
#             and arr.ndim == 1
#             and np.issubdtype(arr.dtype, np.number)
#         ):
#             raw = arr
#             print(f"Using array: {k}")
#             break

#     if raw is None:
#         raise ValueError("No 1D numeric ADC array found in npz.")

# raw = np.asarray(raw).squeeze()

# # Use saved sample rate when available.
# # Otherwise assume approximately 62.5 kS/s.
# if "rate_hz" in data.files:
#     rate_hz = float(np.asarray(data["rate_hz"]).squeeze())
# else:
#     rate_hz = 62_500.0

# print(f"\nSample rate: {rate_hz / 1000:.3f} kS/s")
# print(f"Number of samples: {len(raw)}")
# print(f"Capture duration: {len(raw) / rate_hz:.6f} seconds")

# # Convert sample index to time
# time_s = np.arange(len(raw), dtype=float) / rate_hz
# time_ms = time_s * 1000.0

# plt.figure(figsize=(11, 5))
# plt.plot(time_ms, raw, linewidth=0.8)

# plt.xlabel("Time (ms)")
# plt.ylabel("ADC raw code")
# plt.title(f"ADC capture: {Path(path).name}")
# plt.grid(True)
# plt.tight_layout()

# plt.show()


##  For 7.8kSps
import numpy as np
import matplotlib.pyplot as plt
import sys

# Usage:
# python plot_adc_npz.py your_capture.npz

path = sys.argv[1] if len(sys.argv) > 1 else "ads131_20s_ch1_precise.npz"

data = np.load(path, allow_pickle=True)

print("Keys in npz:")
for k in data.files:
    arr = data[k]
    print(
        f"  {k}: shape={getattr(arr, 'shape', None)}, "
        f"dtype={getattr(arr, 'dtype', None)}"
    )

# Try common names first
if "raw" in data.files:
    raw = data["raw"]
elif "adc" in data.files:
    raw = data["adc"]
elif "samples" in data.files:
    raw = data["samples"]
else:
    # Fallback: first 1D numeric array
    raw = None

    for k in data.files:
        arr = data[k]

        if (
            isinstance(arr, np.ndarray)
            and arr.ndim == 1
            and np.issubdtype(arr.dtype, np.number)
        ):
            raw = arr
            print(f"Using array: {k}")
            break

    if raw is None:
        raise ValueError("No 1D numeric ADC array found in npz.")

raw = np.asarray(raw).squeeze()

# Use saved sample rate if available.
# Otherwise assume 7.8 kS/s.
if "rate_hz" in data.files:
    rate_hz = float(np.asarray(data["rate_hz"]).squeeze())
else:
    rate_hz = 7_800.0

# Convert every sample index to elapsed time
time_s = np.arange(len(raw), dtype=float) / rate_hz

print(f"\nSample rate: {rate_hz:.3f} S/s")
print(f"Number of samples: {len(raw)}")
print(f"Full duration: {len(raw) / rate_hz:.3f} seconds")

plt.figure(figsize=(12, 5))
plt.plot(time_s, raw, linewidth=0.8)

plt.xlabel("Time (s)")
plt.ylabel("ADC raw code")
plt.title(f"ADC capture: {path}")
plt.grid(True)
plt.tight_layout()

print("\nInteractive controls:")
print("  Zoom: magnifying glass icon")
print("  Pan: hand icon")
print("  Reset: home icon")

plt.show()