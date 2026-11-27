// =====================================================================
//  iShara Headband firmware  (ESP32 + MPU6050)
//
//  1) Bluetooth HID mouse  : head tilt moves the cursor (works without the app)
//                            + hardware clicks requested by the app (HID cmd)
//  2) iShara data service  : streams live head data to the desktop app and
//                            receives settings / calibration / commands
//  The personal movement model runs HERE and is saved in flash (NVS).
//
//  Wiring
//    MPU6050 VCC -> 3V3   GND -> GND   SDA -> D21   SCL -> D22   AD0 -> GND
//    Buzzer  +   -> D26   -   -> GND
//  Mounting : upright on the forehead, chip facing forward (sensor Z = forward).
//             The exact tilt is captured at calibration (head frame below);
//             axis swap / direction signs are detected by the app (sw/ix/iy).
//  Library  : ESP32 BLE Mouse (T-vK), patched for ESP32 core 3.x
//             -> vendored in ../libraries/ESP32-BLE-Mouse
//  Protocol : docs/protocol.md  (must match desktop/ishara/protocol.py)
//
//  Sound    : one beep when Bluetooth connects (nothing else)
//  Serial (115200): 'c' = calibrate neutral, 'd' = toggle live readout
// =====================================================================

#include <Wire.h>
#include <BleMouse.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <Preferences.h>

// ---------------- Pins ----------------
#define MPU_ADDR   0x68
#define SDA_PIN    21
#define SCL_PIN    22
#define BUZZER_PIN 26

// ---------------- iShara data service (must match desktop/ishara/protocol.py) ----
#define SVC_UUID  "b7a10001-5f3c-4e2a-9d1b-1a2b3c4d5e6f"
#define DATA_UUID "b7a10002-5f3c-4e2a-9d1b-1a2b3c4d5e6f"   // notify: live head data
#define CMD_UUID  "b7a10003-5f3c-4e2a-9d1b-1a2b3c4d5e6f"   // write : text commands
#define CONF_UUID "b7a10004-5f3c-4e2a-9d1b-1a2b3c4d5e6f"   // read  : current settings

const int REPORT_MS = 15;   // mouse report period
const int STREAM_MS = 33;   // ~30 Hz live data to the app

// ---------------- Personal movement model (saved in NVS) ----------------
// Tilt is normalised by the user's own comfortable range for each side:
//   n = tilt / range_side            (0 = neutral, 1 = comfortable limit)
//   inside dead zone (|n| < dz)      -> no movement (ignores small involuntary motion)
//   u = (|n| - dz) / (1 - dz)  clamped 0..1
//   speed = 1 + (maxSpeed - 1) * u^gamma   (slow start, capped top speed)
struct Model {
  float p0 = 0, r0 = 0;              // neutral pitch / roll (deg)
  float rU = 15, rD = 12;            // comfortable range up / down (deg)
  float rL = 15, rR = 15;            // comfortable range left / right (deg)
  float dz = 0.22;                   // dead zone, fraction of range
  float sx = 6, sy = 5;              // max speed px/report, horizontal / vertical
  float gam = 1.6;                   // curve: >1 = finer control near centre
  float alpha = 0.25;                // smoothing (low-pass), 0..1
  bool  ix = false, iy = false;      // invert axes
  bool  sw = false;                  // swap pitch/roll (set by app calibration)
} M;

Preferences prefs;
BLECharacteristic *dataChar = nullptr, *confChar = nullptr;

float pitchF = 0, rollF = 0;         // smoothed tilt relative to neutral
float gyroBias = 0, gyroNow = 0;
bool  paused = false, calibrating = false, sensorOK = false;
int   lastDx = 0, lastDy = 0;

volatile bool cmdPending = false;
String cmdText;

// ---------------- Buzzer (DISABLED - the Ishara app now speaks instead) ----------------
// To turn the buzzer back on: uncomment the body below and the pinMode lines in setup().
void beep(int ms, int times = 1) {
  // for (int i = 0; i < times; i++) {
  //   digitalWrite(BUZZER_PIN, HIGH); delay(ms);
  //   digitalWrite(BUZZER_PIN, LOW);
  //   if (i < times - 1) delay(100);
  // }
  (void)ms; (void)times;
}

// The only sound the headband makes: one beep when Bluetooth connects.
void connectBeep() {
  digitalWrite(BUZZER_PIN, HIGH); delay(150);
  digitalWrite(BUZZER_PIN, LOW);
}

// ---------------- Settings (NVS + text format "k=v,k=v") ----------------
String modelToText() {
  char buf[240];
  snprintf(buf, sizeof(buf),
           "p0=%.2f,r0=%.2f,rU=%.2f,rD=%.2f,rL=%.2f,rR=%.2f,dz=%.3f,sx=%.2f,sy=%.2f,gam=%.2f,alpha=%.3f,ix=%d,iy=%d,sw=%d",
           M.p0, M.r0, M.rU, M.rD, M.rL, M.rR, M.dz, M.sx, M.sy, M.gam, M.alpha, M.ix, M.iy, M.sw);
  return String(buf);
}

float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Apply "k=v,k=v". Every value is range-checked so bad input can't break the mouse.
void applyText(const String &s) {
  int start = 0;
  while (start < (int)s.length()) {
    int end = s.indexOf(',', start);
    if (end < 0) end = s.length();
    String kv = s.substring(start, end);
    int eq = kv.indexOf('=');
    if (eq > 0) {
      String k = kv.substring(0, eq); k.trim();
      float v = kv.substring(eq + 1).toFloat();
      if      (k == "p0")    M.p0 = clampf(v, -90, 90);
      else if (k == "r0")    M.r0 = clampf(v, -180, 180);
      else if (k == "rU")    M.rU = clampf(v, 4, 60);
      else if (k == "rD")    M.rD = clampf(v, 4, 60);
      else if (k == "rL")    M.rL = clampf(v, 4, 60);
      else if (k == "rR")    M.rR = clampf(v, 4, 60);
      else if (k == "dz")    M.dz = clampf(v, 0.05, 0.6);
      else if (k == "sx")    M.sx = clampf(v, 1, 30);
      else if (k == "sy")    M.sy = clampf(v, 1, 30);
      else if (k == "gam")   M.gam = clampf(v, 1.0, 3.0);
      else if (k == "alpha") M.alpha = clampf(v, 0.05, 1.0);
      else if (k == "ix")    M.ix = v != 0;
      else if (k == "iy")    M.iy = v != 0;
      else if (k == "sw")    M.sw = v != 0;
    }
    start = end + 1;
  }
}

void saveModel() { prefs.putString("model", modelToText()); }
void loadModel() { String s = prefs.getString("model", ""); if (s.length()) applyText(s); }
void publishConf() { if (confChar) confChar->setValue(modelToText()); }

// ---------------- Sensor ----------------
void writeReg(byte reg, byte val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg); Wire.write(val);
  Wire.endTransmission();
}

// Head frame in sensor (fwd, left, z) coordinates, built at calibration from
// the measured gravity direction. Makes tilt independent of how the board sits.
float Ef[3] = {1, 0, 0}, El[3] = {0, 1, 0}, Eu[3] = {0, 0, 1};
float lastG[3] = {0, 0, 1};    // last raw gravity vector (fwd, left, z)

float dot3(const float *a, const float *b) { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]; }
void norm3(float *a) { float n = sqrt(dot3(a, a)); if (n > 1e-6) { a[0] /= n; a[1] /= n; a[2] /= n; } }

// Build the head frame so that "up" = gravity at neutral, forward stays as close
// as possible to the configured forward axis.
void buildFrame(const float *g0) {
  float up[3] = {g0[0], g0[1], g0[2]}; norm3(up);
  // Board is worn upright on the FOREHEAD, chip facing out -> sensor Z = forward.
  // Verified with a live test on the headband (2026-11-27): forward = +Z.
  float ref[3] = {0, 0, 1};
  if (fabs(dot3(ref, up)) > 0.9) { ref[0] = 1; ref[1] = 0; ref[2] = 0; }  // board lying flat: use X
  float d = dot3(ref, up);
  float f[3] = {ref[0] - d*up[0], ref[1] - d*up[1], ref[2] - d*up[2]}; norm3(f);
  // left = up x forward
  float l[3] = {up[1]*f[2] - up[2]*f[1], up[2]*f[0] - up[0]*f[2], up[0]*f[1] - up[1]*f[0]};
  for (int i = 0; i < 3; i++) { Ef[i] = f[i]; El[i] = l[i]; Eu[i] = up[i]; }
}

bool readSensor(float &pitch, float &roll, float &gyro) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(MPU_ADDR, 14) != 14) return false;
  int16_t ax = Wire.read() << 8 | Wire.read();
  int16_t ay = Wire.read() << 8 | Wire.read();
  int16_t az = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read();
  int16_t gx = Wire.read() << 8 | Wire.read();
  int16_t gy = Wire.read() << 8 | Wire.read();
  int16_t gz = Wire.read() << 8 | Wire.read();
  if (ax == 0 && ay == 0 && az == 0) return false;          // invalid reading
  // Raw gravity vector in sensor axes. buildFrame() turns it into head axes
  // at calibration (forward = sensor Z on the forehead mount, verified live).
  float fwd = (float)ax, left = (float)ay;
  lastG[0] = fwd; lastG[1] = left; lastG[2] = (float)az;
  // Tilt relative to the calibrated neutral frame.
  // pitch > 0 = chin up, roll > 0 = head toward right shoulder
  float gf = dot3(lastG, Ef), gl = dot3(lastG, El), gu = dot3(lastG, Eu);
  pitch = atan2(gf, sqrt(gl * gl + gu * gu)) * 180.0 / PI;
  roll  = atan2(gl, gu) * 180.0 / PI;
  gyro  = (fabs(gx) + fabs(gy) + fabs(gz)) / 131.0;
  return true;
}

float wrap180(float a) {
  while (a > 180) a -= 360;
  while (a < -180) a += 360;
  return a;
}

// Capture neutral position (2 s average)
void calibrateNeutral() {
  calibrating = true;
  Serial.println("Calibrating neutral... keep head straight and still");
  beep(300);
  float gsum[3] = {0, 0, 0}, gs = 0; int n = 0;
  unsigned long t = millis();
  while (millis() - t < 2000) {
    float p, r, g;
    if (readSensor(p, r, g)) {
      gsum[0] += lastG[0]; gsum[1] += lastG[1]; gsum[2] += lastG[2];
      gs += g; n++;
    }
    delay(10);
  }
  if (n > 20) {
    // Mounting angles (for info only - the frame below removes them)
    M.p0 = atan2(gsum[0], sqrt(gsum[1]*gsum[1] + gsum[2]*gsum[2])) * 180.0 / PI;
    M.r0 = atan2(gsum[1], gsum[2]) * 180.0 / PI;
    buildFrame(gsum);
    gyroBias = gs / n;
    saveModel(); publishConf();
  }
  pitchF = rollF = 0;
  calibrating = false;
  Serial.printf("Neutral pitch=%.1f roll=%.1f (mounting tilt, compensated)\n", M.p0, M.r0);
  beep(80, 2);
}

// ---------------- Personal mapping ----------------
int axisSpeed(float tilt, float rangeNeg, float rangePos, float maxSpeed) {
  float range = tilt >= 0 ? rangePos : rangeNeg;
  float n = fabs(tilt) / range;
  if (n < M.dz) return 0;
  float u = clampf((n - M.dz) / (1 - M.dz), 0, 1);
  float s = 1 + (maxSpeed - 1) * pow(u, M.gam);
  return (int)round(tilt > 0 ? s : -s);
}

void computeMove(int &dx, int &dy) {
  // roll > 0 = head toward right shoulder (before invert)
  dx = axisSpeed(rollF, M.rL, M.rR, M.sx);
  if (M.ix) dx = -dx;
  // pitch > 0 = chin up -> cursor up (negative screen y)
  dy = -axisSpeed(pitchF, M.rD, M.rU, M.sy);
  if (M.iy) dy = -dy;
}

// ---------------- Commands from the app ----------------
// CAL | PAUSE | RESUME | SET k=v,... | SAVE | RESET | BEEP
void hidCommand(String a);   // defined after bleMouse

void handleCommand(String c) {
  c.trim();
  Serial.println("CMD " + c);
  if (c == "CAL")         calibrateNeutral();
  else if (c == "PAUSE")  paused = true;
  else if (c == "RESUME") paused = false;
  else if (c == "SAVE")   { saveModel(); beep(40); }
  else if (c == "BEEP")   beep(60);
  else if (c == "RESET")  { M = Model(); saveModel(); calibrateNeutral(); }
  else if (c.startsWith("SET ")) applyText(c.substring(4));
  // Hardware clicks over Bluetooth HID. Unlike software clicks, these also work
  // on protected windows (On-Screen Keyboard, admin apps, login prompts).
  else if (c.startsWith("HID ")) { hidCommand(c.substring(4)); return; }
  publishConf();
}

class CmdCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *ch) override {
    cmdText = String(ch->getValue().c_str());
    cmdPending = true;                     // handled in loop(), not in the BLE task
  }
};

// ---------------- BLE mouse + data service ----------------
class IsharaMouse : public BleMouse {
public:
  IsharaMouse() : BleMouse("Ishara Mouse", "Ishara", 100) {}
protected:
  void onStarted(BLEServer *server) override {
    BLEService *svc = server->createService(SVC_UUID);
    dataChar = svc->createCharacteristic(DATA_UUID,
                 BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);
    dataChar->addDescriptor(new BLE2902());
    BLECharacteristic *cmd = svc->createCharacteristic(CMD_UUID,
                 BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    cmd->setCallbacks(new CmdCallbacks());
    confChar = svc->createCharacteristic(CONF_UUID, BLECharacteristic::PROPERTY_READ);
    publishConf();
    svc->start();
  }
};
IsharaMouse bleMouse;

// HID L | R | M | D (double) | DOWN | UP | WHEEL n
void hidCommand(String a) {
  if (!bleMouse.isConnected()) return;
  a.trim();
  if      (a == "L")    bleMouse.click(MOUSE_LEFT);
  else if (a == "R")    bleMouse.click(MOUSE_RIGHT);
  else if (a == "M")    bleMouse.click(MOUSE_MIDDLE);
  else if (a == "B")    bleMouse.click(MOUSE_BACK);
  else if (a == "F")    bleMouse.click(MOUSE_FORWARD);
  else if (a == "D")    { bleMouse.click(MOUSE_LEFT); delay(60); bleMouse.click(MOUSE_LEFT); }
  else if (a == "DOWN") bleMouse.press(MOUSE_LEFT);
  else if (a == "UP")   bleMouse.release(MOUSE_LEFT);
  else if (a.startsWith("WHEEL ")) {
    int n = constrain(a.substring(6).toInt(), -20, 20);
    bleMouse.move(0, 0, (signed char)n);
  }
}

// Live packet (10 bytes, little endian) - see ishara/protocol.py
//  int16 pitch*100, int16 roll*100, int16 gyro*10, int8 dx, int8 dy,
//  uint8 flags (1=paused, 2=calibrating, 4=sensorOK), uint8 seq
void streamData() {
  if (!dataChar) return;
  static uint8_t seq = 0;
  uint8_t b[10];
  int16_t p = (int16_t)clampf(pitchF * 100, -32000, 32000);
  int16_t r = (int16_t)clampf(rollF * 100, -32000, 32000);
  int16_t g = (int16_t)clampf(gyroNow * 10, 0, 32000);
  memcpy(b, &p, 2); memcpy(b + 2, &r, 2); memcpy(b + 4, &g, 2);
  b[6] = (int8_t)lastDx; b[7] = (int8_t)lastDy;
  b[8] = (paused ? 1 : 0) | (calibrating ? 2 : 0) | (sensorOK ? 4 : 0);
  b[9] = seq++;
  dataChar->setValue(b, 10);
  dataChar->notify();
}

// =====================================================================
void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);         // used only for the connect beep
  digitalWrite(BUZZER_PIN, LOW);
  delay(800);

  prefs.begin("ishara", false);
  loadModel();

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() != 0) {
    Serial.println("MPU6050 NOT found! Check wiring.");
    while (true) { beep(1000); delay(1000); }
  }
  writeReg(0x6B, 0x01);   // wake up
  writeReg(0x1A, 0x03);   // low-pass ~44 Hz
  writeReg(0x1B, 0x00);   // gyro  +-250 deg/s
  writeReg(0x1C, 0x00);   // accel +-2 g
  delay(100);
  sensorOK = true;

  bleMouse.begin();
  Serial.println("Bluetooth on: \"Ishara Mouse\"");
  calibrateNeutral();
}

void loop() {
  static bool debugOut = false;                   // 'd' = toggle live readout
  if (Serial.available()) {
    char ch = Serial.read();
    if (ch == 'c') calibrateNeutral();
    else if (ch == 'd') debugOut = !debugOut;
  }
  static unsigned long lastDbg = 0;
  if (debugOut && millis() - lastDbg >= 100) {
    lastDbg = millis();
    Serial.printf("D %.1f %.1f %d %d sw=%d ix=%d iy=%d\n", pitchF, rollF, lastDx, lastDy, M.sw, M.ix, M.iy);
  }
  if (cmdPending) { cmdPending = false; handleCommand(cmdText); }

  float p, r, g;
  sensorOK = readSensor(p, r, g);
  if (sensorOK) {
    // p, r are already relative to neutral (head frame from calibration)
    if (M.sw) { float t = p; p = r; r = t; }
    pitchF = M.alpha * wrap180(p) + (1 - M.alpha) * pitchF;
    rollF  = M.alpha * wrap180(r) + (1 - M.alpha) * rollF;
    gyroNow = fabs(g - gyroBias);
  }

  bool connected = bleMouse.isConnected();
  static bool wasConnected = false;
  if (connected && !wasConnected) {
    Serial.println(">> connected");
    connectBeep();
    BLEDevice::startAdvertising();   // keep advertising so the app can find the data service
  }
  if (!connected && wasConnected) { Serial.println(">> disconnected"); paused = false; }
  wasConnected = connected;

  static unsigned long lastReport = 0, lastStream = 0;
  if (millis() - lastReport >= REPORT_MS) {
    lastReport = millis();
    int dx = 0, dy = 0;
    if (sensorOK && !paused && !calibrating) computeMove(dx, dy);
    lastDx = dx; lastDy = dy;
    if (connected && (dx || dy)) bleMouse.move(dx, dy);
  }
  if (connected && millis() - lastStream >= STREAM_MS) {
    lastStream = millis();
    streamData();
  }
  delay(3);
}
