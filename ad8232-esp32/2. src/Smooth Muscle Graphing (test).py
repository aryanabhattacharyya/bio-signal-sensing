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
FS = 200.0         # Sampling frequency in Hz
NOTCH_FREQ = 60.0  # The frequency of the power line - 60Hz
Q = 30.0           # Quality factor (higher means a narrower, sharper cut)

# --- DESIGN THE NOTCH FILTER ---
# b and a are the filter coefficients derived from the Z-transform
b_notch, a_notch = signal.iirnotch(NOTCH_FREQ, Q, FS)

# --- Setup pyqtgraph ---
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Smooth Muscle Signal Processing")
win.resize(1200, 400)
plot = win.addPlot(title="Smooth Muscle Waveform")
curve = plot.plot(pen='y') # Yellow line

# Lock the Y-axis to 12-bit ADC range (0 to 4095) so it doesn't autoscale!
plot.setYRange(0, 4095) 

# A thread-safe scrolling buffer
data_buffer = deque(maxlen=WINDOW_SIZE)
# Initialize filter state memory so the filter transitions smoothly between samples
filter_state = signal.lfilter_zi(b_notch, a_notch) * 2048

# Setup Real-time Filter
def live_bandpass(data, low=20, high=200, fs=500):
    nyq = 0.5 * fs
    b, a = butter(2, [low/nyq, high/nyq], btype='band')
    return lfilter(b, a, data)

def start_graphing():
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        print(f"Connected to {PORT}. Streaming data... Press Ctrl+C to stop.")

        # Before the while loop starts, initialize the continuous state memory
        filter_state = signal.lfilter_zi(b_notch, a_notch) * 2048  # Midpoint reference

        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        sensor_val = int(line)

                        # 1. Instead of filtering the whole array every time, 
                        # just filter the new incoming value using continuous memory!
                        filtered_val, filter_state = signal.lfilter(b_notch, a_notch, [float(sensor_val)], zi=filter_state)

                        # 2. Add new data to our rolling buffer
                        data_buffer.append(filtered_val[0])
                        #data_array = np.array(list(data_buffer), dtype=float)
                        #filtered_data = signal.lfilter(b_notch, a_notch, data_array)
                        #curve.setData(filtered_data)

                        filtered_data = live_bandpass(data_buffer)
                        # 3. Update the graph with the clean, smooth line
                        #curve.setData(list(data_buffer))
                        curve.setData(list(filtered_data))
                        
                        # 4. Force PyQt to repaint the screen
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
