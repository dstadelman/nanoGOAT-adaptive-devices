# BLE_PROTOCOL — Adaptive Controller

The wire contract between the box and any app. The nanoGOAT AAC app, nRF
Connect, and test scripts all speak exactly this. Timing values and the state
machine behind it are owned by [FIRMWARE](FIRMWARE.md).

## 1. Discovery and connection

- The box is a BLE peripheral. It accepts **one connection at a time** and
  resumes advertising when that connection ends.
- The advertising packet carries the **service UUID**. The scan response carries
  the device name **`nanoGOAT Controller`**. Apps discover the box by filtering
  on the service UUID, not on the name.
- No bonding or OS pairing. An app scans, connects, and uses the service
  directly.

## 2. GATT

Every UUID shares the base `54ce0000-eae9-4eb4-8f51-34fbe6573f4c`. Only the
first 16 bits differ.

| Item | UUID | Properties |
|------|------|-----------|
| Service | `54ce0001-eae9-4eb4-8f51-34fbe6573f4c` | |
| CONTROL | `54ce0002-eae9-4eb4-8f51-34fbe6573f4c` | Write, Write Without Response |
| STATE | `54ce0003-eae9-4eb4-8f51-34fbe6573f4c` | Read, Notify |

All multi-byte integers are **little-endian**.

## 3. CONTROL: commands

Byte 0 is the opcode. The box ignores and logs malformed commands; the relay
state does not change.

| Opcode | Name | Payload | Effect |
|--------|------|---------|--------|
| `0x01` | RUN_TIMED | `u32 duration_ms` | Relay on for `duration_ms`, clamped to the maximum on-time. `0` means the stored default duration. Restarts the timer if already on. |
| `0x02` | RUN_LATCHED | — | Relay on until OFF, disconnect, or the maximum on-time. |
| `0x03` | OFF | — | Relay off immediately. |
| `0x04` | TOGGLE | — | Relay off if on; otherwise RUN_LATCHED. |
| `0x05` | HOLD | — | Direct mode. Relay on, and stays on only while HOLD arrives at least once per heartbeat timeout. Each HOLD resets the heartbeat timer, not the maximum on-time. |
| `0x10` | SET_DEFAULT_DURATION | `u32 duration_ms` | Stores the default timed duration (persists across power cycles), clamped to the maximum on-time. |

Example: run for 5 seconds = `01 88 13 00 00`.

## 4. STATE: status

17 bytes. Readable at any time. Notified on every change, and once per second
while the relay is on.

| Offset | Type | Field | Values |
|--------|------|-------|--------|
| 0 | u8 | protocol_version | `1` |
| 1 | u8 | relay | `0` off · `1` on |
| 2 | u8 | mode | `0` idle · `1` timed · `2` latched · `3` direct |
| 3 | u8 | last_off_reason | `0` boot · `1` OFF command · `2` timer done · `3` max on-time · `4` heartbeat lost · `5` disconnect · `6` low battery · `7` error |
| 4 | u32 | remaining_ms | Time until the relay turns off on its own; `0` when off |
| 8 | u16 | battery_mv | Battery voltage in mV; `0` when not measured |
| 10 | u32 | default_duration_ms | Stored default for RUN_TIMED |
| 14 | u16 | heartbeat_timeout_ms | HOLD must arrive within this interval |
| 16 | u8 | max_on_s | Hard maximum on-time, in seconds |

## 5. App obligations

- Treat STATE as the only truth about the relay. Never assume a command took
  effect until STATE says so.
- In direct mode, send HOLD at **no more than half** the heartbeat timeout.
- The app is never needed to turn the relay off. The box turns it off on its
  own ([SAFETY](SAFETY.md) §2).
