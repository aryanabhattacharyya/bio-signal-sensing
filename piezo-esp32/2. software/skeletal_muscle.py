import serial
import sys
import time
import numpy as np
import keyboard
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5 import QtWidgets, QtCore

# --- CONFIGURATION ---
PORT = 'COM7' 
BAUD_RATE = 115200

# --- Setup pyqtgraph ---
app = QtWidgets.QApplication(sys.argv)
win = pg.GraphicsLayoutWidget(show=True, title="Skeletal Muscle Signal Processing")
win.resize(800, 400)
plot = win.addPlot(title="Real-Time Differential EMG/Transduction Waveform")
curve = plot.plot(pen='y') # Yellow line
plot.setYRange(-4000, 4000)
# Data windows
plot_window = 200 # Show exactly 1 second of rolling data at 200Hz

def start_triple_logging():
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
        
        session_id = int(time.time())
        
        raw_filename = f"Skeletal_Raw_Data_{session_id}.csv"
        sum_filename = f"Skeletal_Summary_Data_{session_id}.tsv"
        
        # Open both files
        with open(raw_filename, "w") as raw_f, open(sum_filename, "w") as sum_f:
            # Headers
            raw_f.write("Unix_Time_MS,Raw_Value\n")
            sum_f.write("Timestamp\tMin\tMax\tAvg\tStDev\tFlag\n")
            
            print(f"Triple Logging Active!")
            print(f"  > RAW: {raw_filename}")
            print(f"  > SUMMARY: {sum_filename}")

            while True:
                second_data = []
                start_time = time.time()
                
                # Collect for 1 second
                while time.time() - start_time < 1.0:
                    differential_signal = 0
                    if ser.in_waiting > 0:
                        try:
                            line = ser.readline().decode('utf-8').strip()
                            data = line.split(',')
            
                            if len(data) == 2:
                                sensor_A0 = int(data[0])
                                sensor_A7 = int(data[1])
                
                                # Calculate your common-mode rejection output (can be positive or negative)
                                differential_signal = sensor_A0 - sensor_A7
                
                                # 1. IMMEDIATELY WRITE TO RAW FILE
                                raw_f.write(f"{int(time.time()*1000)},{differential_signal}\n")
                                second_data.append(differential_signal)

                                if len(second_data) > 0:
                                    # 2. SHOW THE LAST 200 READINGS ON GRAPH
                                    curve.setData(second_data[-200:])
                                    # force a refresh of the screen because this is inside
                                    # a while true loop
                                    QtGui.QGuiApplication.processEvents()
                
                        except (ValueError, IndexError):
                            # Pass over startup fragments or bad characters
                            pass

                # 3. CALCULATE SUMMARY FOR EXCEL

                # Include a flag in case subject does something that is worth noting
                current_flag = ""

                if keyboard.is_pressed('f') or keyboard.is_pressed('F'):
                    current_flag = "Tensed Forearm"
                    print("--> FLAG: Tensed Forearm")
                elif keyboard.is_pressed('t') or keyboard.is_pressed('T'):
                    current_flag = "Tensed Forearm - Strong"
                    print("--> FLAG: Tensed Forearm - Strong")
                elif keyboard.is_pressed('b') or keyboard.is_pressed('B'):
                    current_flag = "Flex - Strong"
                    print("--> FLAG: Moving")
                elif keyboard.is_pressed('g') or keyboard.is_pressed('G'):
                    current_flag = "Flex - Gentle"
                    print("--> FLAG: Flex - Gentle")
                elif keyboard.is_pressed('d') or keyboard.is_pressed('D'):
                    current_flag = "Drumming"
                    print("--> FLAG: Drumming")
                elif keyboard.is_pressed('e') or keyboard.is_pressed('E'):
                    current_flag = "Externally, moved finger"
                    print("--> FLAG: Externally, moved finger")
                
                if second_data:
                    low = min(second_data)
                    high = max(second_data)
                    avg = int(np.mean(second_data))
                    stdev = np.std(second_data)
                    timestamp = time.strftime("%H:%M:%S")
                    
                    sum_f.write(f"{timestamp}\t{low}\t{high}\t{avg}\t{stdev}\t{current_flag}\t\n")
                    print(f"[{timestamp}] Summary Logged: Max {high}, StDev {stdev:.2f}, Flag: {current_flag}")
    except KeyboardInterrupt:
        print(f"\nSession Ended. Files saved.")

if __name__ == "__main__":
    start_triple_logging()
