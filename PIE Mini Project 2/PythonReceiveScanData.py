# MP2 3D Scanner

import serial  # pyright: ignore[reportMissingModuleSource]
import csv
import time

# this expects the Arduino to be running ArduinoScanSweep.ino, which
# sends one line per data point formatted as "panAngle,tiltAngle,rawValue"

arduinoComPort = "COM3"
baudRate = 9600

serialPort = serial.Serial(arduinoComPort, baudRate, timeout=1)
time.sleep(2)  # give the Arduino time to reset after the serial port opens

outputFilename = "scan_data.csv"

scanData = []  # list of (panAngle, tiltAngle, rawSensorValue) tuples

print("receiving scan data. press Ctrl+C to quit.")

try:
  while True:
    lineOfData = serialPort.readline().decode().strip()

    if len(lineOfData) == 0:
      continue

    # convert the line into 3 integers; skip any partial line
    try:
      panAngle, tiltAngle, rawValue = (int(x) for x in lineOfData.split(','))
    except ValueError:
      continue

    scanData.append((panAngle, tiltAngle, rawValue))
    print("pan = " + str(panAngle), end="")
    print(", tilt = " + str(tiltAngle), end="")
    print(", raw = " + str(rawValue))

except KeyboardInterrupt:
  print("Stopped by user.")

finally:
  serialPort.close()

  # save everything collected so far to a CSV for calibration/visualization later
  with open(outputFilename, "w", newline="") as csvFile:
    writer = csv.writer(csvFile)
    writer.writerow(["pan_angle_deg", "tilt_angle_deg", "raw_sensor_value"])
    writer.writerows(scanData)

  print("Saved " + str(len(scanData)) + " points to " + outputFilename)