// MP2 3D Scanner

#include <Servo.h>

Servo panServo;               // sweeps left/right
Servo tiltServo;              // sweeps up/down

const int panServoPin  = 9;
const int tiltServoPin = 10;
const int sensorPin    = A0;  // analog output

// sweep range/step settings TUNE LATER
// units are degrees, matching Servo.write()
const int panMin   = 50;
const int panMax   = 150;
const int panStep  = 1;    // Servo.write() only has 1-degree resolution, so 0.5 truncated to 0 and never advanced

const int tiltMin  = 50;
const int tiltMax  = 130;
const int tiltStep = 1;    // same as panStep

const int settleDelay = 150;   // ms to let the servo/sensor settle before reading
const int numSamples   = 5;    // number of ADC readings averaged per point


void setup()
{
  long baudRate = 9600;        // must match the baud rate in the Python script
  Serial.begin(baudRate);

  panServo.attach(panServoPin);
  tiltServo.attach(tiltServoPin);

  panServo.write(panMin);
  tiltServo.write(tiltMin);
  delay(500);                  // give servos time to reach the starting position
}


// take several ADC readings and average them to reduce noise
int readDistanceRaw()
{
  long total = 0;
  for (int i = 0; i < numSamples; i++) {
    total += analogRead(sensorPin);
    delay(2);
  }
  return total / numSamples;
}



// send one data point back to the laptop as "panAngle,tiltAngle,rawValue"
void sendDataPoint(int panAngle, int tiltAngle, int rawValue)
{
  Serial.print(panAngle);   Serial.print(",");
  Serial.print(tiltAngle);  Serial.print(",");
  Serial.println(rawValue);
}


// raster-scan the sensor across the pan/tilt range one time
// then stop (so the scan doesn't repeat and confuse the data being collected)
void loop()
{
  for (int tiltAngle = tiltMin; tiltAngle <= tiltMax; tiltAngle += tiltStep) {
    tiltServo.write(tiltAngle);
    delay(settleDelay);

    // alternate sweep direction each row so we don't waste
    // time snapping the pan servo back to panMin before every row
    bool sweepingForward = (((tiltAngle - tiltMin) / tiltStep) % 2 == 0);

    if (sweepingForward) {
      for (int panAngle = panMin; panAngle <= panMax; panAngle += panStep) {
        panServo.write(panAngle);
        delay(settleDelay);
        int rawValue = readDistanceRaw();
        sendDataPoint(panAngle, tiltAngle, rawValue);
      }
    } else {
      for (int panAngle = panMax; panAngle >= panMin; panAngle -= panStep) {
        panServo.write(panAngle);
        delay(settleDelay);
        int rawValue = readDistanceRaw();
        sendDataPoint(panAngle, tiltAngle, rawValue);
      }
    }
  }

  while (true) {
    delay(1000);
  }
}
