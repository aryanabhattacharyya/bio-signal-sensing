import serial
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtGui
from collections import deque
from scipy import signal # For signal processing
from scipy.signal import butter, lfilter

# --- CONFIGURATION ---
PORT = 'COM7' 
BAUD_RATE = 115200
WINDOW_SIZE = 500  # Show exactly 1 second of rolling data at 500Hz
FS = 500.0         # Sampling frequency in Hz
NOTCH_FREQ = 60.0  # The frequency of the power line - 60Hz
Q = 30.0           # Quality factor (higher means a narrower, sharper cut)
BANDPASS_LOW = 20.0  # Muscle signal high-pass cutoff
BANDPASS_HIGH = 200.0  # Upper frequency cutoff

# RMS & Scaling Config
RMS_WINDOW = 25  # ~50ms sliding window at 500Hz for RMS smoothing
ENABLE_RMS = True  # Toggle RMS envelope
ENABLE_LOG = True  # Toggle Logarithmic scaling

# --- DESIGN THE FILTERS ---
# 1. 60Hz Notch Filter
b_notch, a_notch = signal.iirnotch(NOTCH_FREQ, Q, FS)

# 2. 20Hz - 200Hz Bandpass Filter
nyq = 0.5 * FS
b_pass, a_pass = butter(2, [BANDPASS_LOW / nyq, BANDPASS_HIGH / nyq], btype="band")

# --- Setup pyqtgraph ---
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Smooth Muscle Signal Processing")
#win.resize(1200, 400)
WINDOW_SIZE = 500
plot = win.addPlot(title="Smooth Muscle Waveform")
curve = plot.plot(pen='y') # Yellow line

# Adjust Y-Range based on processing mode:
# If RMS/Log is ON, output is strictly positive and compressed (~0 to 3.0)
if ENABLE_RMS and ENABLE_LOG:
  plot.setYRange(0, 3.0)
elif ENABLE_RMS:
  plot.setYRange(0, 500)
else:
  plot.setYRange(-500, 500)
  
plot.showGrid(x=True, y=True)
  
# A thread-safe scrolling buffer
data_buffer = deque(maxlen=WINDOW_SIZE)

def calculate_envelope(buffer_data):
  """Computes RMS and optional Log10 scale over the rolling window."""
  arr = np.array(buffer_data)

  if not ENABLE_RMS:
    return arr

  # 1. Rolling RMS over RMS_WINDOW samples
  #    Square -> Uniform moving average -> Square root
  kernel = np.ones(RMS_WINDOW) / RMS_WINDOW
  rms = np.sqrt(np.convolve(arr**2, kernel, mode="same"))

  # 2. Log Dynamic Range Compression
  if ENABLE_LOG:
    # log10(RMS + 1) expands subtle micro-signals and compresses giant spikes
    return np.log10(rms + 1.0)

  return rms

def start_graphing():
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected to {PORT}. Streaming data... Press Ctrl+C to stop.")

        # Before the while loop starts, initialize the continuous state memory
        notch_state = signal.lfilter_zi(b_notch, a_notch) * 2048
        bandpass_state = signal.lfilter_zi(b_pass, a_pass) * 0

        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        sensor_val = float(line)

                        # 1. Continuous 60Hz Notch Filter
                        notch_val, notch_state = signal.lfilter(b_notch, a_notch, [sensor_val], zi=notch_state)
                        
                        # 2. Continuous Bandpass Filter (Removes baseline drift & centers around 0)
                        bp_val, bandpass_state = signal.lfilter(b_pass, a_pass, notch_val, zi=bandpass_state)
                        
                        # 3. Append filtered sample to rolling buffer
                        data_buffer.append(bp_val[0])

                        # 4. Compute Envelope and Paint
                        if len(data_buffer) >= RMS_WINDOW:
                            display_data = calculate_envelope(data_buffer)
                            curve.setData(display_data)

                        # 5. Force PyQt to repaint the screen
                        QtWidgets.QApplication.processEvents()
                        
                except (ValueError, IndexError):
                    pass # Ignore partial serial fragments
                    
    except KeyboardInterrupt:
        print("\nSession Ended")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    start_graphing()
