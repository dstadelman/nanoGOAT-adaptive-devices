// nanoGOAT Adaptive Controller firmware.
//
// Behavior: _specs/FIRMWARE.md   Wire format: _specs/BLE_PROTOCOL.md
// Pins:     _specs/HARDWARE.md   Invariants:  _specs/SAFETY.md
//
// BLE callbacks never touch the relay. They queue events; loop() is the single
// owner of the relay pin and applies every deadline.

#include <BLEDevice.h>
#include <BLEServer.h>
#include <Preferences.h>

#define FW_VERSION "0.1.0"
#define PROTOCOL_VERSION 1

// Set to 1 once the R1/R2 divider is wired to A0 (FIRMWARE.md §5).
#ifndef BATTERY_SENSE
#define BATTERY_SENSE 0
#endif

// ---- Pins (HARDWARE.md §2) ----
static const int PIN_RELAY = D10;       // GPIO18, high = relay on
static const int PIN_STATUS_LED = D9;   // GPIO20, high = lit
static const int PIN_VSENSE = A0;       // GPIO0, battery / 2
static const int PIN_ONBOARD_LED = 15;  // user LED, active low, mirrors relay

// ---- Values (FIRMWARE.md §2) ----
static const uint32_t MAX_ON_MS = 60000;
static const uint8_t MAX_ON_S = MAX_ON_MS / 1000;
static const uint32_t DEFAULT_DURATION_MS = 5000;
static const uint16_t HEARTBEAT_TIMEOUT_MS = 1500;
static const uint16_t LOW_BATTERY_WARN_MV = 3600;
static const uint16_t LOW_BATTERY_CUTOFF_MV = 3400;
static const uint32_t NOTIFY_WHILE_ON_MS = 1000;

// ---- Protocol (BLE_PROTOCOL.md) ----
#define SERVICE_UUID "54ce0001-eae9-4eb4-8f51-34fbe6573f4c"
#define CONTROL_UUID "54ce0002-eae9-4eb4-8f51-34fbe6573f4c"
#define STATE_UUID "54ce0003-eae9-4eb4-8f51-34fbe6573f4c"
#define DEVICE_NAME "nanoGOAT Controller"

enum Opcode : uint8_t {
  OP_RUN_TIMED = 0x01,
  OP_RUN_LATCHED = 0x02,
  OP_OFF = 0x03,
  OP_TOGGLE = 0x04,
  OP_HOLD = 0x05,
  OP_SET_DEFAULT_DURATION = 0x10,
};

enum Mode : uint8_t { MODE_IDLE = 0, MODE_TIMED = 1, MODE_LATCHED = 2, MODE_DIRECT = 3 };

enum OffReason : uint8_t {
  OFF_BOOT = 0,
  OFF_COMMAND = 1,
  OFF_TIMER = 2,
  OFF_MAX_ON = 3,
  OFF_HEARTBEAT = 4,
  OFF_DISCONNECT = 5,
  OFF_LOW_BATTERY = 6,
  OFF_ERROR = 7,
};

static const char *MODE_NAMES[] = {"idle", "timed", "latched", "direct"};
static const char *REASON_NAMES[] = {"boot", "command", "timer", "max_on",
                                     "heartbeat", "disconnect", "low_battery", "error"};

// Events handed from BLE callbacks to loop().
enum EventType : uint8_t { EV_COMMAND, EV_CONNECT, EV_DISCONNECT };
struct Event {
  EventType type;
  uint8_t len;
  uint8_t data[8];
};

static QueueHandle_t events;
static BLECharacteristic *stateChar;
static Preferences prefs;

// ---- Relay state, owned by loop() ----
static bool relayOn = false;
static Mode mode = MODE_IDLE;
static OffReason lastOffReason = OFF_BOOT;
static uint32_t maxOnDeadline = 0;     // absolute millis
static uint32_t modeDeadline = 0;      // timer end (timed) or heartbeat end (direct)
static bool connected = false;
static uint32_t defaultDurationMs = DEFAULT_DURATION_MS;
static uint16_t batteryMv = 0;
static bool stateDirty = true;
static uint32_t lastNotify = 0;

static void logf(const char *fmt, ...) {
  char buf[160];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  Serial.printf("[%7lu] %s\n", (unsigned long)millis(), buf);
}

static bool deadlinePassed(uint32_t deadline, uint32_t now) {
  return (int32_t)(now - deadline) >= 0;
}

static uint32_t remainingMs(uint32_t now) {
  if (!relayOn) return 0;
  uint32_t end = maxOnDeadline;
  if ((mode == MODE_TIMED || mode == MODE_DIRECT) && (int32_t)(modeDeadline - end) < 0) {
    end = modeDeadline;
  }
  return deadlinePassed(end, now) ? 0 : end - now;
}

static void writeRelay(bool on) {
  digitalWrite(PIN_RELAY, on ? HIGH : LOW);
  digitalWrite(PIN_ONBOARD_LED, on ? LOW : HIGH);
}

static void relayOff(OffReason reason) {
  writeRelay(false);
  if (relayOn) logf("RELAY OFF reason=%s", REASON_NAMES[reason]);
  relayOn = false;
  mode = MODE_IDLE;
  lastOffReason = reason;
  stateDirty = true;
}

// The only path that turns the relay on (FIRMWARE.md §3).
static void relayOn_(Mode newMode, uint32_t modeMs, uint32_t now) {
  if (BATTERY_SENSE && batteryMv != 0 && batteryMv < LOW_BATTERY_CUTOFF_MV) {
    logf("REJECT run: battery %umV below cutoff", batteryMv);
    relayOff(OFF_LOW_BATTERY);
    return;
  }
  maxOnDeadline = now + MAX_ON_MS;
  modeDeadline = now + min(modeMs, MAX_ON_MS);
  mode = newMode;
  relayOn = true;
  writeRelay(true);
  lastOffReason = OFF_BOOT;  // not meaningful while on; reported only after the next off
  stateDirty = true;
  logf("RELAY ON mode=%s remaining=%lu", MODE_NAMES[mode], (unsigned long)remainingMs(now));
}

static uint32_t readU32(const uint8_t *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void handleCommand(const Event &ev, uint32_t now) {
  if (ev.len == 0) {
    logf("REJECT empty command");
    return;
  }
  uint8_t op = ev.data[0];
  switch (op) {
    case OP_RUN_TIMED: {
      if (ev.len != 5) break;
      uint32_t ms = readU32(ev.data + 1);
      if (ms == 0) ms = defaultDurationMs;
      logf("CMD RUN_TIMED %lu", (unsigned long)ms);
      relayOn_(MODE_TIMED, ms, now);
      return;
    }
    case OP_RUN_LATCHED:
      if (ev.len != 1) break;
      logf("CMD RUN_LATCHED");
      relayOn_(MODE_LATCHED, MAX_ON_MS, now);
      return;
    case OP_OFF:
      if (ev.len != 1) break;
      logf("CMD OFF");
      relayOff(OFF_COMMAND);
      return;
    case OP_TOGGLE:
      if (ev.len != 1) break;
      logf("CMD TOGGLE");
      if (relayOn) relayOff(OFF_COMMAND);
      else relayOn_(MODE_LATCHED, MAX_ON_MS, now);
      return;
    case OP_HOLD:
      if (ev.len != 1) break;
      if (relayOn && mode == MODE_DIRECT) {
        // Heartbeat: extend the heartbeat deadline only, never the max on-time.
        modeDeadline = now + HEARTBEAT_TIMEOUT_MS;
      } else {
        logf("CMD HOLD");
        relayOn_(MODE_DIRECT, HEARTBEAT_TIMEOUT_MS, now);
      }
      return;
    case OP_SET_DEFAULT_DURATION: {
      if (ev.len != 5) break;
      uint32_t ms = min(readU32(ev.data + 1), MAX_ON_MS);
      if (ms == 0) break;
      defaultDurationMs = ms;
      prefs.putULong("default_ms", ms);
      stateDirty = true;
      logf("CMD SET_DEFAULT_DURATION %lu", (unsigned long)ms);
      return;
    }
  }
  logf("REJECT op=0x%02X len=%u", op, ev.len);
}

// ---- BLE ----

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *) override {
    Event ev = {EV_CONNECT, 0, {}};
    xQueueSend(events, &ev, 0);
  }
  void onDisconnect(BLEServer *) override {
    // Queued to loop(); the relay turns off within one loop pass.
    Event ev = {EV_DISCONNECT, 0, {}};
    xQueueSend(events, &ev, 0);
  }
};

class ControlCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String v = c->getValue();
    Event ev = {EV_COMMAND, 0, {}};
    if (v.length() > sizeof(ev.data)) {
      ev.len = 0xFF;  // oversized: rejected in loop()
    } else {
      ev.len = v.length();
      memcpy(ev.data, v.c_str(), v.length());
    }
    xQueueSend(events, &ev, 0);
  }
};

static void publishState(uint32_t now) {
  uint8_t s[17];
  uint32_t rem = remainingMs(now);
  s[0] = PROTOCOL_VERSION;
  s[1] = relayOn ? 1 : 0;
  s[2] = mode;
  s[3] = lastOffReason;
  memcpy(s + 4, &rem, 4);
  memcpy(s + 8, &batteryMv, 2);
  memcpy(s + 10, &defaultDurationMs, 4);
  uint16_t hb = HEARTBEAT_TIMEOUT_MS;
  memcpy(s + 14, &hb, 2);
  s[16] = MAX_ON_S;
  stateChar->setValue(s, sizeof(s));
  if (connected) stateChar->notify();
  lastNotify = now;
  stateDirty = false;
}

static void setupBle() {
  BLEDevice::init(DEVICE_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService *service = server->createService(SERVICE_UUID);

  BLECharacteristic *control = service->createCharacteristic(
      CONTROL_UUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  control->setCallbacks(new ControlCallbacks());

  stateChar = service->createCharacteristic(
      STATE_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  // The BLE stack adds the notify descriptor (CCCD) itself.

  service->start();

  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);  // name goes in the scan response (BLE_PROTOCOL.md §1)
  BLEDevice::startAdvertising();
  logf("ADV start");
}

// ---- Battery ----

static void sampleBattery() {
#if BATTERY_SENSE
  uint32_t sum = 0;
  for (int i = 0; i < 16; i++) sum += analogReadMilliVolts(PIN_VSENSE);
  uint16_t mv = (sum / 16) * 2;
  if (mv / 50 != batteryMv / 50) stateDirty = true;  // notify on 50mV steps
  batteryMv = mv;
#endif
}

static bool batteryLow() {
  return BATTERY_SENSE && batteryMv != 0 && batteryMv < LOW_BATTERY_WARN_MV;
}

// ---- Status LED (PRODUCT.md §5) ----

static void updateStatusLed(uint32_t now) {
  bool lit;
  if (relayOn) lit = (now / 60) % 2;             // quick flash
  else if (batteryLow()) lit = (now / 125) % 2;  // rapid blink
  else if (connected) lit = true;                // solid
  else lit = (now / 1000) % 2;                   // slow blink
  digitalWrite(PIN_STATUS_LED, lit ? HIGH : LOW);
}

// ---- Serial status (FIRMWARE.md §6) ----

// Any input from a Serial Monitor prints a STATUS line, so a person can see
// the board is alive without pressing a button. One message (with or without
// a line ending) prints one line.
static void handleSerialInput() {
  if (Serial.available() <= 0) return;
  delay(20);  // let the rest of the message arrive
  while (Serial.available() > 0) Serial.read();
  logf("STATUS fw=%s ble=%s relay=%s mode=%s last_off=%s battery_mv=%u", FW_VERSION,
       connected ? "connected" : "advertising", relayOn ? "on" : "off", MODE_NAMES[mode],
       REASON_NAMES[lastOffReason], batteryMv);
}

// ---- Main ----

void setup() {
  // Relay off before anything else (SAFETY.md §2).
  pinMode(PIN_RELAY, OUTPUT);
  digitalWrite(PIN_RELAY, LOW);
  pinMode(PIN_ONBOARD_LED, OUTPUT);
  digitalWrite(PIN_ONBOARD_LED, HIGH);
  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);

  Serial.begin(115200);
  delay(300);  // give USB CDC a moment so the boot line is not lost
  logf("BOOT fw=%s proto=%d battery_sense=%d", FW_VERSION, PROTOCOL_VERSION, BATTERY_SENSE);

  events = xQueueCreate(16, sizeof(Event));
  prefs.begin("controller", false);
  defaultDurationMs = min((uint32_t)prefs.getULong("default_ms", DEFAULT_DURATION_MS), MAX_ON_MS);

#if BATTERY_SENSE
  analogSetAttenuation(ADC_11db);
#endif
  sampleBattery();
  setupBle();
  publishState(millis());
}

void loop() {
  uint32_t now = millis();

  Event ev;
  while (xQueueReceive(events, &ev, 0) == pdTRUE) {
    switch (ev.type) {
      case EV_CONNECT:
        connected = true;
        stateDirty = true;
        logf("CONNECT");
        break;
      case EV_DISCONNECT:
        connected = false;
        logf("DISCONNECT");
        relayOff(OFF_DISCONNECT);
        BLEDevice::startAdvertising();
        logf("ADV start");
        break;
      case EV_COMMAND:
        handleCommand(ev, now);
        break;
    }
  }

  if (relayOn) {
    if (deadlinePassed(maxOnDeadline, now)) {
      relayOff(OFF_MAX_ON);
    } else if (mode == MODE_TIMED && deadlinePassed(modeDeadline, now)) {
      relayOff(OFF_TIMER);
    } else if (mode == MODE_DIRECT && deadlinePassed(modeDeadline, now)) {
      relayOff(OFF_HEARTBEAT);
    }
  }

  static uint32_t lastBattery = 0;
  if (now - lastBattery >= 1000) {
    lastBattery = now;
    sampleBattery();
    if (relayOn && BATTERY_SENSE && batteryMv != 0 && batteryMv < LOW_BATTERY_CUTOFF_MV) {
      relayOff(OFF_LOW_BATTERY);
    }
  }

  if (stateDirty || (relayOn && now - lastNotify >= NOTIFY_WHILE_ON_MS)) {
    publishState(now);
  }

  handleSerialInput();
  updateStatusLed(now);
  delay(5);
}
