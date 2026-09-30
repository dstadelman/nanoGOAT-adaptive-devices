# PRODUCT — Adaptive Controller

## 1. Goal

The Adaptive Controller lets the nanoGOAT AAC app run a switch-adapted toy.
A child taps a word such as "more bubbles" on their AAC board, and the toy runs.
The request is communicated with language, and the world responds.

## 2. What it is

A small battery-powered Bluetooth Low Energy (BLE) box with one 3.5mm mono
output jack. When the app commands it, the box closes a relay across the jack's
tip and sleeve for a bounded time.

This is the same electrical interface every commercial accessibility switch
uses (e.g. AbleNet Big Red). To a toy, the box is indistinguishable from a
person pressing a switch. Therefore:

- Any toy adapted for the box also works with an ordinary accessibility switch.
- Any commercially switch-adapted toy works with the box.

## 3. Users

| User | Needs |
|------|-------|
| AAC user (child) | Taps a word; the toy responds quickly and reliably. |
| Caregiver / therapist | Charges the box, plugs in a toy, pairs it in the app, and trusts it will not leave a toy running. |
| Maker | Builds the box from the specs in this folder with hand tools and a soldering iron. |

## 4. Operating modes

The app selects the mode per command. [SAFETY](SAFETY.md) bounds every mode.

| Mode | Pairs with | Behavior |
|------|-----------|----------|
| **Timed** (default) | A single word ("more bubbles") | The toy runs for a set duration, then stops. The box owns the timer; the app sends one command. |
| **Latched** | A word pair ("go" / "stop") | The toy runs until a stop command, disconnect, or the maximum on-time, whichever comes first. |
| **Direct** | Press-and-hold in the app | The toy runs only while the app keeps sending heartbeats. It stops as soon as heartbeats stop. |

The timed duration is a setting stored on the box. It is never longer than the
maximum on-time in [SAFETY](SAFETY.md).

## 4a. Response time

A child taps a word and expects the toy to answer at once. A delay the child
can notice breaks the link between the word and the result.

| Span | Limit |
|------|-------|
| Tap on the AAC board → toy starts | under **500 ms** |
| Command arrives at the box → relay closed | under **50 ms** |

The app holds the connection open before the child taps. Connecting takes
seconds, so a tap never waits for a connection. Every command is sent the
moment it is tapped, never behind an earlier command that has not completed.

## 5. Status LED

One LED on the outside of the box shows the state.

| Pattern | Meaning |
|---------|---------|
| Slow blink | On, advertising, waiting for the app |
| Solid | Connected to the app |
| Quick flash | Relay on (toy running) |
| Rapid blink | Battery low; charge soon |
| Off | Power switch off, or battery empty |

## 6. Everyday use

- **Power:** a slide switch on the box turns it on and off. Off fully
  disconnects the battery.
- **Charging:** USB-C. The power switch must be **on** to charge, because the
  charger is on the controller board, downstream of the switch. The box works
  normally while charging.
- **Connecting a toy:** a 3.5mm mono cable runs from the box's jack to the toy's
  jack.
- **Connecting the app:** the app scans for the box and connects directly. The
  box needs no pairing in the phone's Bluetooth settings.

## 7. Scope

In scope: one output, battery toys, control from the nanoGOAT AAC app.

Out of scope: nanoGOAT app changes (the BLE protocol spec defines the contract
the app implements), multiple outputs, a physical switch input on the box,
custom PCB, and 3D-printed enclosure.
