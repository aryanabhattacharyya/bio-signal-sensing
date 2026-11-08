from collections import deque
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import serial
from scipy import signal
from scipy.signal import butter

# --- CONFIGURATION ---
PORT = "COM7"
BAUD_RATE = 115200
FS = 500.0         # Sampling frequency in Hz
NOTCH_FREQ = 60.0  # The frequency of the power line - 60Hz
Q = 30.0           # Quality factor (higher means a narrower, sharper cut)

# --- SIGNAL RANGES ---
# Skeletal muscle
BANDPASS_LOW = 20.0    # Muscle signal high-pass cutoff
BANDPASS_HIGH = 200.0  # Upper frequency cutoff
WINDOW_SIZE = 500  # Show 1 second of rolling data at 500Hz

# Smooth muscle
#BANDPASS_LOW = 0.01    # ~0.6 cycle per minute
#BANDPASS_HIGH = 0.25   # ~15 cycle per minute
#WINDOW_SIZE = 3000     # Show 1-2 full minutes of data

# RMS & Scaling Config
RMS_WINDOW = 25  # ~50ms sliding window
ENABLE_RMS = True
ENABLE_LOG = True

# --- DESIGN FILTERS ---
# 1. 60Hz Notch Filter
b_notch, a_notch = signal.iirnotch(NOTCH_FREQ, Q, FS)

# 2. 20Hz - 200Hz Bandpass Filter
nyq = 0.5 * FS
b_pass, a_pass = butter(2, [BANDPASS_LOW / nyq, BANDPASS_HIGH / nyq], btype="band")

# --- SETUP PYQTGRAPH ---
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Smooth Muscle Signal Processing")
plot = win.addPlot(title="Smooth Muscle Envelope")
curve = plot.plot(pen="y")

if ENABLE_RMS and ENABLE_LOG:
  plot.setYRange(0, 3.0)
elif ENABLE_RMS:
  plot.setYRange(0, 500)
else:
  plot.setYRange(-500, 500)

plot.showGrid(x=True, y=True)

# A thread-safe scrolling buffer
data_buffer = deque(maxlen=WINDOW_SIZE)

# Initialize Serial Connection
try:
  ser = serial.Serial(PORT, BAUD_RATE, timeout=0.01)
  print(f"Connected to {PORT}. Streaming data...")
except Exception as e:
  print(f"Failed to connect to {PORT}: {e}")
  sys.exit(1)

# Initialize filter state memory
notch_state = signal.lfilter_zi(b_notch, a_notch) * 2048
bandpass_state = signal.lfilter_zi(b_pass, a_pass) * 0


def calculate_envelope(buffer_data):
  #Computes RMS and optional Log10 scale over the rolling window.
  arr = np.array(buffer_data)
  if not ENABLE_RMS:
    return arr

  kernel = np.ones(RMS_WINDOW) / RMS_WINDOW
  rms = np.sqrt(np.convolve(arr**2, kernel, mode="same"))

  if ENABLE_LOG:
    return np.log10(rms + 1.0)
  return rms


def update():
  #Runs periodically via QTimer: reads all available serial data and updates the plot.
  global notch_state, bandpass_state

  try:
    # Read ALL available bytes in the serial buffer at once to prevent overflow
    while ser.is_open and ser.in_waiting > 0:
      line = ser.readline().decode("utf-8", errors="ignore").strip()
      if line:
        try:
          sensor_val = float(line)

          # 1. Continuous Notch
          notch_val, notch_state = signal.lfilter(b_notch, a_notch, [sensor_val], zi=notch_state)

          # 2. Continuous Bandpass
          bp_val, bandpass_state = signal.lfilter(b_pass, a_pass, notch_val, zi=bandpass_state)

          # 3. Append to buffer
          data_buffer.append(bp_val[0])

        except ValueError:
          pass  # Skip corrupted floating numbers or partial strings

  except serial.SerialException:
    # Safely handle temporary serial glitches without crashing Python
    pass

  # Redraw graph once per QTimer tick (30 FPS) rather than on every single byte
  if len(data_buffer) >= RMS_WINDOW:
    display_data = calculate_envelope(data_buffer)
    curve.setData(display_data)


# --- START TIMER (30 FPS / ~33ms refresh rate) ---
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(33)

if __name__ == "__main__":
  try:
    sys.exit(app.exec())
  finally:
    if "ser" in locals() and ser.is_open:
      ser.close()
      print("Serial connection closed.")
