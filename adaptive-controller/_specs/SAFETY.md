# SAFETY — Adaptive Controller

These invariants override every other spec. A design that satisfies a feature
but breaks an invariant is wrong.

## 1. Electrical scope

- The box switches **low-voltage, battery-powered toys only.** It is never
  connected to anything mains-powered, directly or through an adapter.
- The toy's circuit touches only the relay contacts. The toy's battery and the
  box's electronics share no conductor.

## 2. The relay is off unless something keeps it on

The box never depends on an "off" message arriving. The relay is **off** in
each of these conditions:

| Condition | Mechanism |
|-----------|-----------|
| Power-up, reset, or brownout | Hardware: 10kΩ pull-down on the relay input ([HARDWARE](HARDWARE.md) §3). Firmware drives the pin low before it does anything else. |
| Maximum on-time reached, in any mode | Firmware timer, independent of the app |
| BLE disconnect | Firmware |
| Direct mode heartbeat missed | Firmware |
| Any firmware error or unexpected state | Firmware fails to off |
| Battery below the cutoff voltage | Firmware refuses to turn the relay on |

## 3. Maximum on-time

- A single, compiled-in **hard maximum on-time** caps every activation in every
  mode. No command or stored setting can exceed it.
- The user-adjustable timed duration and any latched run are clamped to it.
- After the relay turns off at the hard maximum, it stays off until a new,
  separate command arrives. Nothing re-triggers it automatically.

The specific values (hard maximum, default timed duration, heartbeat interval,
battery cutoff) are owned by the firmware spec.

## 4. Battery

- The LiPo has its own protection circuit.
- JST battery connectors have no standard polarity. The battery connector's
  polarity is checked with a multimeter before the battery is ever connected
  to the controller board.
- The battery is never charged unattended while damaged, swollen, or hot.

## 5. Toy side

- Solder joints and the added jack inside a toy are sealed so bubble solution
  or other liquid cannot reach them.
- Adding the jack leaves the toy's own switch working.
