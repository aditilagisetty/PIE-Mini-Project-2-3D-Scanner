# MP2 3D Scanner - calibration helper
# Run this while ArduinoCalibrate.ino is uploaded to the board.
#
# Steps through a fixed list of distances (5in to 30in, step 5in).
# For each: press Enter once the square is positioned, it records
# exactly 10 raw readings, then stops and waits for you to move the
# square and press Enter again for the next distance.
#
# Note: this sensor's response is non-monotonic below ~20cm (~7.9in),
# its rated minimum range - the 5in point is below that, so it's
# collected but excluded from the automatic curve fit.
#
# Every individual reading is saved to calibration_data.csv for
# PythonPlotCalibration.py. Run with "validation" as an argument
# (python PythonCalibrationHelper.py validation) to instead record a
# second set of distances NOT used in the fit to validation_data.csv -
# those are what the error plot should be made from.

import csv
import serial
import sys
import time
import math

validationMode = len(sys.argv) > 1 and sys.argv[1] == "validation"

arduinoComPort = "COM3"
baudRate = 9600

serialPort = serial.Serial(arduinoComPort, baudRate, timeout=1)
time.sleep(2)

adcMax = 1023
vRef = 5.0
minValidCm = 20.0  # sensor's rated minimum reliable range

if validationMode:
  distancesIn = [12, 17, 22, 27]  # in between the fit distances
  outputFilename = "validation_data.csv"
else:
  distancesIn = [5, 10, 15, 20, 25, 30]
  outputFilename = "calibration_data.csv"
readingsPerDistance = 10

samples = []     # list of (distance_cm, avg_raw_value)
rawReadings = [] # list of (distance_in, distance_cm, raw_value), every reading

try:
  for distanceIn in distancesIn:
    input("\nPosition the square at " + str(distanceIn) + " in, then press Enter...")

    serialPort.reset_input_buffer()

    readings = []
    while len(readings) < readingsPerDistance:
      line = serialPort.readline().decode(errors="replace").strip()
      if line.isdigit():
        readings.append(int(line))

    avgRaw = sum(readings) / len(readings)
    distanceCm = distanceIn * 2.54
    print("  " + str(distanceIn) + "in (" + str(round(distanceCm, 1)) + "cm) -> avg raw = "
          + str(round(avgRaw, 1)) + " (" + str(len(readings)) + " samples)")
    samples.append((distanceCm, avgRaw))
    for r in readings:
      rawReadings.append((distanceIn, distanceCm, r))

except KeyboardInterrupt:
  print("\nStopped early by user.")

finally:
  serialPort.close()

# save every reading so the plots can be made later without re-measuring
with open(outputFilename, "w", newline="") as csvFile:
  writer = csv.writer(csvFile)
  writer.writerow(["distance_in", "distance_cm", "raw_sensor_value"])
  writer.writerows(rawReadings)
print("\nSaved " + str(len(rawReadings)) + " readings to " + outputFilename)

if validationMode:
  sys.exit(0)  # validation points must not be used in the fit

print("\nCollected points (distance_cm, raw):")
for distanceCm, avgRaw in samples:
  print("  " + str(round(distanceCm, 1)) + " cm, raw=" + str(round(avgRaw, 1)))

# fit distance = calibA * voltage^calibB  <=>  ln(distance) = ln(calibA) + calibB * ln(voltage)
usable = [(d, r) for d, r in samples if r > 0 and d >= minValidCm]
skipped = [(d, r) for d, r in samples if not (r > 0 and d >= minValidCm)]

if skipped:
  print("\nExcluded from fit (below " + str(minValidCm) + "cm or invalid):")
  for d, r in skipped:
    print("  " + str(round(d, 1)) + " cm, raw=" + str(round(r, 1)))

if len(usable) < 2:
  print("\nNot enough valid samples to fit a curve.")
else:
  xs = [math.log((r / adcMax) * vRef) for d, r in usable]
  ys = [math.log(d) for d, r in usable]
  n = len(xs)
  meanX = sum(xs) / n
  meanY = sum(ys) / n
  b = sum((x - meanX) * (y - meanY) for x, y in zip(xs, ys)) / sum((x - meanX) ** 2 for x in xs)
  lnA = meanY - b * meanX
  a = math.exp(lnA)
  print("\nFitted calibration (update these in PythonVisualizeScanData.py):")
  print("  calibA = " + str(round(a, 3)))
  print("  calibB = " + str(round(b, 3)))
