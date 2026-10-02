# MP2 2.5D Scanner

A pan/tilt scanner built from two hobby servos and a Sharp GP2Y0A02YK0F IR
distance sensor. The Arduino raster-scans the sensor across the target and
streams `pan,tilt,raw` readings to a laptop, where Python converts the raw
readings to distances and plots the scanned shape.

```
pip install pyserial matplotlib numpy
```

## Files

| File | Runs on | Purpose |
|---|---|---|
| `ArduinoCalibrate/ArduinoCalibrate.ino` | Arduino | Holds the sensor straight ahead and streams averaged raw ADC readings for calibration |
| `PythonCalibrationHelper.py` | Laptop | Steps through known distances, records 10 readings at each, saves them to CSV and prints a fit |
| `PythonPlotCalibration.py` | Laptop | Fits the calibration curve and makes the calibration plot and error plot |
| `ArduinoScanSweep/ArduinoScanSweep.ino` | Arduino | Raster-scans pan/tilt and sends one `pan,tilt,raw` line per point |
| `PythonReceiveScanData.py` | Laptop | Reads the serial stream and saves it to `scan_data.csv` |
| `PythonVisualizeScanData.py` | Laptop | Converts a scan CSV to XYZ points and plots front and top-down views |

## Wiring

| Part | Arduino pin |
|---|---|
| Pan servo signal | D9 |
| Tilt servo signal | D10 |
| IR sensor output (white) | A0 |
| Servo and sensor power / ground | 5V / GND |

Set `arduinoComPort` in the Python scripts to your board's port (default `COM3`).

## 1. Calibrate the sensor

Upload `ArduinoCalibrate.ino`, then:

```
python PythonCalibrationHelper.py              # 5-30 in  -> calibration_data.csv
python PythonCalibrationHelper.py validation   # 12, 17, 22, 27 in -> validation_data.csv
python PythonPlotCalibration.py calibration_data.csv validation_data.csv
```

This saves `calibration_plot.png` (sensor voltage vs. actual distance with the
fitted curve) and `error_plot.png` (predicted vs. actual distance for the
validation distances, which are **not** used in the fit). It also prints the
fitted constants and the error at each distance.

Copy the printed `calibA` / `calibB` into `PythonVisualizeScanData.py`.

### Calibration function

The sensor's output voltage falls off roughly as 1/distance, so we model it as
a power law:

```
distance_cm = calibA * voltage ^ calibB        (calibB is close to -1)
voltage     = raw_adc / 1023 * 5.0
```

Taking the log of both sides gives a straight line,
`ln(d) = ln(calibA) + calibB * ln(V)`, so `calibA` and `calibB` come from a
least-squares line fit in log-log space. Readings closer than 20 cm are
excluded: below that the sensor's output drops again, so one voltage maps to
two different distances. Readings are also treated as invalid beyond 150 cm,
where the output is too flat and noisy to be useful.

## 2. Scan

Upload `ArduinoScanSweep.ino`, then:

```
python PythonReceiveScanData.py                      # Ctrl+C when the sweep finishes
python PythonVisualizeScanData.py scan_data.csv
```

The visualizer saves `scan_data_front.png` (the shape viewed from the scanner,
colored by depth) and `scan_data_topdown.png` (top-down view, shape vs. wall).
For the CA-provided shape, rename the CSV first (e.g. `ca_shape.csv`) so its
images are saved separately.

Sweep range, step size and settle time are constants at the top of
`ArduinoScanSweep.ino`.
