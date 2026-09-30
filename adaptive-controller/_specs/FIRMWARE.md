# FIRMWARE — Adaptive Controller

Firmware behavior, timing values, and build. The wire format is owned by
[BLE_PROTOCOL](BLE_PROTOCOL.md); pins by [HARDWARE](HARDWARE.md); the
invariants it enforces by [SAFETY](SAFETY.md).

## 1. Platform

- **Arduino framework** on the Espressif `esp32` core, board **XIAO_ESP32C6**,
  built with `arduino-cli`. Seeed documents the XIAO ESP32C6 Arduino-first, the
  core includes BLE, and viewers can build it from the Arduino IDE.
- Source: [`../firmware/adaptive_controller/`](../firmware/adaptive_controller/).
- USB CDC on boot is enabled, so serial logs appear on the USB-C port.

## 2. Values

| Value | Setting |
|-------|---------|
| Hard maximum on-time | **60 s**, compiled in |
| Default timed duration | **5 s**, changeable with SET_DEFAULT_DURATION |
| Heartbeat timeout (direct mode) | **1500 ms** |
| Low-battery warning | below **3.60 V** |
| Low-battery cutoff (relay refuses to turn on) | below **3.40 V** |
| STATE notify while on | every **1 s** |

## 3. State machine

One loop owns the relay pin. Every path that turns the relay on goes through a
single function that checks the battery cutoff and sets a deadline no later
than *now + hard maximum*. The loop turns the relay off when any deadline passes
(timer, maximum on-time, heartbeat) and records the reason.

| From | Event | To |
|------|-------|----|
| any | boot | idle (relay off, reason `boot`) |
| idle | RUN_TIMED / RUN_LATCHED / TOGGLE / HOLD | timed / latched / latched / direct |
| on (any mode) | another run command | the new mode; deadlines recomputed; maximum on-time counts from this command |
| on (any mode) | OFF, TOGGLE, deadline passed, disconnect, battery below cutoff, error | idle |

The first statement in `setup()` drives the relay pin low. The hardware
pull-down ([HARDWARE](HARDWARE.md) §3) covers the time before that.

## 4. Indicators

- **Status LED (D9):** the patterns in [PRODUCT](PRODUCT.md) §5.
- **Onboard user LED (GPIO15):** mirrors the relay. It is lit while the relay
  is on. This lets the firmware and app be tested on a bare XIAO with nothing
  wired to it.

## 5. Battery sensing

Battery sensing is a build option, `BATTERY_SENSE`. With it off (bare-board
builds without the divider), `battery_mv` reports `0` and the low-battery rules
are skipped. With it on, the firmware averages 16 ADC samples of VSENSE and
doubles them (1:2 divider).

## 6. Serial log

115200 baud over USB. One line per event, prefixed with milliseconds since
boot, so a test harness can parse it:

```
[   1234] BOOT fw=0.1.0 proto=1
[   1240] ADV start
[   5012] CONNECT
[   6100] CMD RUN_TIMED 5000
[   6100] RELAY ON mode=timed remaining=5000
[  11100] RELAY OFF reason=timer
[  15000] DISCONNECT
```

Every relay transition, command, connection change, and rejected command is
logged.
