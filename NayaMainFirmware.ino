#include <NewPing.h>

#define SONAR1_ECHO_PIN 4
#define SONAR1_TRIG_PIN 5

#define SONAR2_ECHO_PIN 2
#define SONAR2_TRIG_PIN 3

#define SONAR3_ECHO_PIN 6
#define SONAR3_TRIG_PIN 7
#define pwm 10

#define MAX_DISTANCE1 20
#define MAX_DISTANCE2 20
#define MAX_DISTANCE3 30

NewPing sonar1(SONAR1_TRIG_PIN, SONAR1_ECHO_PIN, MAX_DISTANCE1);
NewPing sonar2(SONAR2_TRIG_PIN, SONAR2_ECHO_PIN, MAX_DISTANCE2);
NewPing sonar3(SONAR3_TRIG_PIN, SONAR3_ECHO_PIN, MAX_DISTANCE3);

int jarak1 = 0;
int jarak2 = 0;
int jarak3 = 0;

unsigned long previousMillis = 0;
unsigned long pwmDelay = 100;
bool pwmActive = false;
int speed;
bool run;

const long interval = 500;

void setup() {
  Serial.begin(9600);
  pinMode(pwm, OUTPUT);
  pinMode(A0, INPUT);
}

void loop() {
  unsigned long currentMillis = millis();

  speed = map(analogRead(A0), 0, 1023, 0, 255);

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    jarak1 = sonar1.ping_cm();
    jarak2 = sonar2.ping_cm();
    jarak3 = sonar3.ping_cm();

    Serial.print("Jarak Sensor 1: ");
    Serial.print(jarak1);
    Serial.print(" cm\t");

    Serial.print("Jarak Sensor 2: ");
    Serial.print(jarak2);
    Serial.print(" cm\t");

    Serial.print("Jarak Sensor 3: ");
    Serial.print(jarak3);
    Serial.println(" cm");

    bool logic1 = (jarak1 != 0 && jarak1 < MAX_DISTANCE1);
    bool logic2 = (jarak2 != 0 && jarak2 < MAX_DISTANCE2);
    bool logic3 = (jarak3 != 0 && jarak3 < MAX_DISTANCE3);

    if (logic3 || logic2) {
      run = true;
    } else if (logic1) {
      run = false;
    }
    if (run) {
      analogWrite(pwm, speed);
    } else {
      analogWrite(pwm, 0);
    }
  }
}