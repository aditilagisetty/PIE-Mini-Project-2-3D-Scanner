# MP2 2.5D Scanner - calibration and error plots

# pip install matplotlib numpy
#
# usage:
#   python PythonPlotCalibration.py calibration_data.csv validation_data.csv
#
# both CSVs come from PythonCalibrationHelper.py
# columns: distance_in, distance_cm, raw_sensor_value
#
# Figure 1 (calibration_plot.png): sensor voltage vs. actual distance, with
#   the fitted calibration curve drawn through it.
# Figure 2 (error_plot.png): predicted distance vs. actual distance, and the
#   error, for the validation distances (NOT used in the fit).
#   If no validation file is given, it falls back to the calibration points,
#   which only shows how well the curve fits its own data.
#
# CALIBRATION FUNCTION
# The Sharp GP2Y0A02YK0F outputs a voltage that falls off roughly as
# 1/distance (datasheet fig. "analog output voltage vs distance"), so we
# model it as a power law:
#
#     distance = calibA * voltage ^ calibB      (calibB should be near -1)
#
# Taking ln of both sides makes it a straight line:
#
#     ln(distance) = ln(calibA) + calibB * ln(voltage)
#
# so calibA and calibB come from an ordinary least-squares line fit in
# log-log space. Only points >= minRange are used: below ~20 cm the sensor's
# output drops again, so one voltage maps to two distances and the fit breaks.

import csv
import sys

import numpy as np
import matplotlib.pyplot as plt

calibFilename = sys.argv[1] if len(sys.argv) > 1 else "calibration_data.csv"
validFilename = sys.argv[2] if len(sys.argv) > 2 else None

adcMax   = 1023
vRef     = 5.0   # ADC reference voltage (Arduino UNO runs off 5V)
minRange = 20.0  # cm, fit only uses points at or beyond this


# returns arrays of actual distance (cm) and raw reading, one per row
def loadReadings(filename):
  distances, raws = [], []
  with open(filename, newline="") as csvFile:
    reader = csv.DictReader(csvFile)
    for row in reader:
      distances.append(float(row["distance_cm"]))
      raws.append(float(row["raw_sensor_value"]))
  return np.array(distances), np.array(raws)


def voltageFromRaw(raw):
  return (raw / adcMax) * vRef


def distanceFromVoltage(voltage):
  return calibA * np.power(voltage, calibB)


# least-squares fit of ln(distance) = ln(A) + B*ln(voltage)
# returns (A, B, rSquared); rSquared is computed in log-log space
def fitPowerLaw(distances, voltages):
  lnV = np.log(voltages)
  lnD = np.log(distances)
  b, lnA = np.polyfit(lnV, lnD, 1)
  residuals = lnD - (lnA + b * lnV)
  rSquared = 1 - np.sum(residuals ** 2) / np.sum((lnD - lnD.mean()) ** 2)
  return np.exp(lnA), b, rSquared


# averages readings taken at the same distance
# returns (distances, mean, std) arrays
def groupByDistance(distances, values):
  unique = np.unique(distances)
  means = np.array([values[distances == d].mean() for d in unique])
  stds  = np.array([values[distances == d].std() for d in unique])
  return unique, means, stds


# ---- calibration plot ----
calibDist, calibRaw = loadReadings(calibFilename)
calibVolt = voltageFromRaw(calibRaw)
inFit = (calibDist >= minRange) & (calibVolt > 0)

calibA, calibB, rSquared = fitPowerLaw(calibDist[inFit], calibVolt[inFit])
print("Fitted calibration from " + calibFilename + ":")
print("  distance = " + str(round(calibA, 3)) + " * voltage^" + str(round(calibB, 3))
      + "   (R^2 = " + str(round(rSquared, 4)) + " in log-log space)")
print("  -> set calibA/calibB in PythonVisualizeScanData.py to these values")

groupDist, groupVolt, groupStd = groupByDistance(calibDist, calibVolt)
groupInFit = groupDist >= minRange

fig1, ax1 = plt.subplots(figsize=(8, 6))

# individual readings, faded, so the spread at each distance is visible
ax1.scatter(calibDist[inFit], calibVolt[inFit], s=10, alpha=0.3,
            color="tab:blue", label="Individual readings")
ax1.scatter(calibDist[~inFit], calibVolt[~inFit], s=10, alpha=0.3,
            color="tab:gray", label="Readings below " + str(int(minRange)) + " cm (not fit)")

# mean at each distance with a +/- 1 std error bar
ax1.errorbar(groupDist[groupInFit], groupVolt[groupInFit], yerr=groupStd[groupInFit],
             fmt="o", color="tab:blue", capsize=4, label="Mean ± 1 std")
ax1.errorbar(groupDist[~groupInFit], groupVolt[~groupInFit], yerr=groupStd[~groupInFit],
             fmt="o", color="tab:gray", capsize=4)

# fitted curve, drawn as voltage vs. distance (inverse of distanceFromVoltage)
curveDist = np.linspace(minRange, max(calibDist.max(), 80), 200)
curveVolt = np.power(curveDist / calibA, 1.0 / calibB)
ax1.plot(curveDist, curveVolt, color="tab:orange", linewidth=2,
         label="Fit: d = " + str(round(calibA, 2)) + " · V^(" + str(round(calibB, 3))
               + "),  R² = " + str(round(rSquared, 3)))

ax1.set_xlabel("Actual distance (cm)")
ax1.set_ylabel("Sensor output (V)")
ax1.set_title("IR Sensor Calibration")
ax1.set_xlim(0, curveDist.max() * 1.05)
ax1.grid(alpha=0.3)
ax1.legend()
fig1.tight_layout()
fig1.savefig("calibration_plot.png", dpi=200)


# ---- error plot ----
if validFilename:
  errDist, errRaw = loadReadings(validFilename)
  uniqueIn = sorted(set(round(d / 2.54) for d in errDist))
  distList = ", ".join(str(d) for d in uniqueIn) + " in"
  errSource = "held-out validation set (" + distList + " - NOT used in the calibration fit)"
else:
  errDist, errRaw = calibDist[inFit], calibRaw[inFit]
  errSource = "calibration points (in-sample fit check, not true validation)"
  print("No validation file given - error plot uses the calibration points themselves.")

predicted = distanceFromVoltage(voltageFromRaw(errRaw))
error = predicted - errDist

groupErrDist, groupPred, groupPredStd = groupByDistance(errDist, predicted)
groupErr = groupPred - groupErrDist

fig2, (axPred, axErr) = plt.subplots(1, 2, figsize=(12, 5))

# predicted vs actual - a perfect sensor sits on the dashed line
lineMax = max(errDist.max(), predicted.max()) * 1.1
axPred.plot([0, lineMax], [0, lineMax], "--", color="gray", label="Ideal (predicted = actual)")
axPred.scatter(errDist, predicted, s=10, alpha=0.3, color="tab:blue", label="Individual readings")
axPred.errorbar(groupErrDist, groupPred, yerr=groupPredStd, fmt="o",
                color="tab:blue", capsize=4, label="Mean ± 1 std")
axPred.set_xlim(0, lineMax)
axPred.set_ylim(0, lineMax)
axPred.set_aspect("equal", adjustable="box")
axPred.set_xlabel("Actual distance (cm)")
axPred.set_ylabel("Predicted distance (cm)")
axPred.set_title("Predicted vs. Actual")
axPred.grid(alpha=0.3)
axPred.legend()

# error at each distance
axErr.axhline(0, color="gray", linestyle="--")
axErr.scatter(errDist, error, s=10, alpha=0.3, color="tab:red", label="Individual readings")
axErr.errorbar(groupErrDist, groupErr, yerr=groupPredStd, fmt="o",
               color="tab:red", capsize=4, label="Mean ± 1 std")
axErr.set_xlabel("Actual distance (cm)")
axErr.set_ylabel("Error: predicted − actual (cm)")
axErr.set_title("Measurement Error")
axErr.grid(alpha=0.3)
axErr.legend()

fig2.suptitle("Calibration Error - " + errSource)
fig2.tight_layout()
fig2.savefig("error_plot.png", dpi=200)

# print a summary for the write-up
print("\nError summary (" + errSource + "):")
for d, e, s in zip(groupErrDist, groupErr, groupPredStd):
  print("  " + str(round(d, 1)) + " cm: mean error = " + str(round(e, 2))
        + " cm (" + str(round(100 * e / d, 1)) + "%), std = " + str(round(s, 2)) + " cm")
print("  overall mean absolute error = " + str(round(np.abs(error).mean(), 2)) + " cm")

print("\nSaved calibration_plot.png and error_plot.png")

plt.show()
