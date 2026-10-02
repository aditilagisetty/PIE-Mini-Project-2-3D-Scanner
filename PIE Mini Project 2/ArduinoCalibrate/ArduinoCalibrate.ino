// MP2 3D Scanner - calibration helper
// Holds the sensor pointed straight ahead and streams raw ADC readings
// so known-distance measurements can be taken for calibrating
// calibA/calibB in PythonVisualizeScanData.py.

#include <Servo.h>

Servo panServo;
Servo tiltServo;

const int panServoPin  = 9;
const int tiltServoPin = 10;
const int sensorPin    = A0;

const int numSamples = 10;   // more averaging than the scan sketch, since we're holding still

int readDistanceRaw()
{
  long total = 0;
  for (int i = 0; i < numSamples; i++) {
    total += analogRead(sensorPin);
    delay(2);
  }
  return total / numSamples;
}

void setup()
{
  Serial.begin(9600);
  panServo.attach(panServoPin);
  tiltServo.attach(tiltServoPin);
  panServo.write(90);   // straight ahead
  tiltServo.write(90);  // level
  delay(500);
}

void loop()
{
  Serial.println(readDistanceRaw());
  delay(300);
}
