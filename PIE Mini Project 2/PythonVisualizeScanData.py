# MP2 2.5D Scanner - scan visualization

# pip install matplotlib numpy

import csv
import math
import sys

import numpy as np
import matplotlib.pyplot as plt

# reads the CSV written by PythonReceiveScanData.py
# columns: pan_angle_deg, tilt_angle_deg, raw_sensor_value
#
# usage: python PythonVisualizeScanData.py scan_data.csv
# saves <csv name>_front.png and <csv name>_topdown.png next to the CSV,
# so scanning the CA shape to a different CSV gives separate images

inputFilename = sys.argv[1] if len(sys.argv) > 1 else "scan_data.csv"

# calibration: raw ADC reading -> distance in cm
# The sensor outputs a voltage that is bascially proportional to 1/distance.

# every unit varies
# TUNE THIS by taking a few readings at known distances using a ruler
# and adjusting calibA/calibB until distanceFromRaw()
# matches
adcMax    = 1023
vRef      = 5.0     # runs adc off of 5V
calibA    = 61.211  # fitted 2026-09-28 from calibration_data.csv (R^2 = 0.9913)
calibB    = -1.03
minRange  = 20.0    # cm, below this the sensor's output is ambiguous
maxRange  = 150.0   # cm, above this the sensor's output is unreliable

# straight-ahead servo angles - must match the midpoint of panMin/panMax and
# tiltMin/tiltMax in ArduinoScanSweep.ino, NOT necessarily 90
panCenter  = 100.0  # (panMin + panMax) / 2 = (50 + 150) / 2
tiltCenter = 90.0   # (tiltMin + tiltMax) / 2 = (50 + 130) / 2

# takes a raw adc value and turns it into a distance based
# on the formula and returns it if it is valid
def distanceFromRaw(rawValue):
  voltage = (rawValue / adcMax) * vRef
  if voltage <= 0:
    return None
  distanceCm = calibA * math.pow(voltage, calibB)
  if distanceCm < minRange or distanceCm > maxRange:
    return None
  return distanceCm


# load scan and convert each point to Cartesian XYZ
# pan/tilt are servo angles in degrees (0-180)
# 90 is straight ahead for pan and level for tilt 
# X = left/right, Y = forward depth, Z = up/down.

# 4 empty lists to collect x y and z coords of every valid point
xs, ys, zs, dists = [], [], [], []
azimuths, elevations = [], []  # radians, kept for the polar plots
skippedOutOfRange = 0

# open csv and read every row as a dictionary so we can get
# columns by name instead of position
with open(inputFilename, newline="") as csvFile:
  reader = csv.DictReader(csvFile)
  for row in reader:
    # convert text to numbers
    panAngle  = float(row["pan_angle_deg"])
    tiltAngle = float(row["tilt_angle_deg"])
    rawValue  = float(row["raw_sensor_value"])

    # dont plot if out of range
    distanceCm = distanceFromRaw(rawValue)
    if distanceCm is None:
      skippedOutOfRange += 1
      continue

    # angles of how off center sensor is
    azimuth   = math.radians(panAngle - panCenter)
    elevation = math.radians(tiltAngle - tiltCenter)

    # convert distance and angles to catesian coords
    xs.append(distanceCm * math.cos(elevation) * math.sin(azimuth))
    ys.append(distanceCm * math.cos(elevation) * math.cos(azimuth))
    zs.append(distanceCm * math.sin(elevation))
    # save distance for plot
    dists.append(distanceCm)
    azimuths.append(azimuth)
    elevations.append(elevation)

# sanity check to see how many points were saved and skipped 
# help us see if our calibration range is reasonable
print("Loaded " + str(len(dists)) + " points ("
      + str(skippedOutOfRange) + " skipped as out of sensor range).")

if len(dists) == 0:
  print("Nothing to plot.")
  sys.exit(1)

# convert to numpy arrays for easier math
xs, ys, zs, dists = np.array(xs), np.array(ys), np.array(zs), np.array(dists)
azimuths, elevations = np.array(azimuths), np.array(elevations)

# plot
# depth (Y - forward) is dropped as a spatial axis and shown as color instead,
# so this is a 2D scatter over X (left/right) and Z (up/down) - like a range image
fig, ax = plt.subplots(figsize=(9, 7))

# sequential colormap
# plot every point in 2d space (left/right, up/down), colored by distance
scatter = ax.scatter(xs, zs, c=dists, cmap="viridis", s=12)

# label plot
colorBar = fig.colorbar(scatter, ax=ax, shrink=0.8, pad=0.03)
colorBar.set_label("Distance (cm)")

ax.set_xlabel("X - left/right (cm)")
ax.set_ylabel("Z - up/down (cm)")
ax.set_title("3D Scan Point Cloud (depth shown as color)")

# equal aspect ratio so the shape isn't visually distorted
ax.set_aspect("equal", adjustable="box")

# clean layout
plt.tight_layout()

# top-down view: X (left/right) vs Y (forward depth)
# the shape shows up as a band of points closer than the wall behind it
figTop, axTop = plt.subplots(figsize=(9, 6))
axTop.scatter(xs, ys, c=dists, cmap="viridis", s=6)
axTop.scatter([0], [0], marker="^", color="black", s=80, label="Scanner")
axTop.set_xlabel("X - left/right (cm)")
axTop.set_ylabel("Y - forward depth (cm)")
axTop.set_title("Top-Down View (shape vs. background)")
axTop.set_aspect("equal", adjustable="box")
axTop.legend()
figTop.tight_layout()

# polar versions of the same two views, for comparison against the
# rectangular (Cartesian) ones above
#
# top-down polar: theta = azimuth (pan offset from center), r = horizontal
# distance (= dist * cos(elevation), i.e. distance projected flat, ignoring
# height) - same data as the rectangular top-down view, just in polar form
horizDist = np.sqrt(xs ** 2 + ys ** 2)

# side polar: theta = elevation (tilt offset from center), r = vertical-plane
# distance (= dist * cos(azimuth)) - the elevation-sweep analog of the
# top-down polar plot above
vertDist = np.sqrt(ys ** 2 + zs ** 2)


def polarWedgePlot(theta, r, title, rMax=None):
  fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
  sc = ax.scatter(theta, r, c=dists, cmap="viridis", s=6)
  ax.set_theta_zero_location("N")   # straight ahead points "up"
  ax.set_theta_direction(-1)        # positive angle sweeps to the right
  # zoom the wedge to just the angular range actually scanned, with a
  # little padding, instead of showing a mostly-empty full circle
  thetaMinDeg = math.degrees(theta.min()) - 5
  thetaMaxDeg = math.degrees(theta.max()) + 5
  ax.set_thetamin(thetaMinDeg)
  ax.set_thetamax(thetaMaxDeg)
  if rMax is not None:
    ax.set_rmax(rMax)              # crop out the far wall so the near shape fills the plot
  ax.set_title(title)
  cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.1)
  cb.set_label("Distance (cm)")
  fig.tight_layout()
  return fig


# cap the radial (distance) axis on the two sweep plots so the shape - which
# sits close to the scanner - isn't squashed into a tiny wedge near the
# origin by the much farther wall/background points
zoomRadiusCm = 70.0

figTopPolar = polarWedgePlot(azimuths, horizDist, "Top-Down View (Polar) - azimuth sweep", rMax=zoomRadiusCm)
figSidePolar = polarWedgePlot(elevations, vertDist, "Side View (Polar) - elevation sweep", rMax=zoomRadiusCm)

# front-view polar: a genuine polar analog of the front (image-plane) view,
# using BOTH angles at once instead of collapsing to a single sweep -
# theta = compass angle around the boresight (0 deg = pan right & level,
# 90 deg = straight up), r = angular distance from dead center. This keeps
# the same left/right - up/down layout as the front Cartesian plot, just in
# polar form.
compassTheta = np.arctan2(elevations, azimuths)
angularRadius = np.sqrt(azimuths ** 2 + elevations ** 2)

figFrontPolar, axFrontPolar = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
scFront = axFrontPolar.scatter(compassTheta, angularRadius, c=dists, cmap="viridis", s=6)
axFrontPolar.set_rmax(angularRadius.max() * 1.05)
axFrontPolar.set_title("Front View (Polar) - angle from center vs. compass direction")
cbFront = figFrontPolar.colorbar(scFront, ax=axFrontPolar, shrink=0.7, pad=0.1)
cbFront.set_label("Distance (cm)")
figFrontPolar.tight_layout()

# save images for the write-up, named after the input CSV
baseName = inputFilename.rsplit(".", 1)[0]
fig.savefig(baseName + "_front.png", dpi=200)
figTop.savefig(baseName + "_topdown.png", dpi=200)
figTopPolar.savefig(baseName + "_topdown_polar.png", dpi=200)
figSidePolar.savefig(baseName + "_side_polar.png", dpi=200)
figFrontPolar.savefig(baseName + "_front_polar.png", dpi=200)
print("Saved " + baseName + "_front.png, " + baseName + "_topdown.png, "
      + baseName + "_topdown_polar.png, " + baseName + "_side_polar.png and "
      + baseName + "_front_polar.png")

plt.show()
