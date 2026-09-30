# Adaptive Controller

A small battery-powered Bluetooth box that lets the
[nanoGOAT AAC](https://nanogoat.com) app run a switch-adapted toy. A child taps
"more bubbles" on their communication board, the box closes a switch for a few
seconds, and the bubble machine runs.

The box plugs into a toy through a standard 3.5mm headphone-size jack. This is
the same plug that accessibility switches such as the AbleNet Big Red use.

## Where this project is

The firmware runs on a bare XIAO ESP32C6 board, and a computer can control it
over Bluetooth. The box itself (relay, battery, jack, enclosure) is designed
but not yet built.

This guide lists only steps that were done and checked, on **Windows 11**.
[What has not been tried yet](#what-has-not-been-tried-yet) lists the rest.

## 1. What you need

| Item | Notes |
|------|-------|
| **Seeed Studio XIAO ESP32C6** | Make sure it says **ESP32C6**. Other XIAO boards need different settings. |
| **USB-C cable** | It must carry data, not only charge. |
| **A Windows computer** | About **8 GB** of free disk space for the tools, and Bluetooth for step 5. |

No soldering is needed for this guide. The board's small **orange LED** stands
in for the toy.

## 2. Install Arduino IDE

Arduino IDE turns the firmware source code into a program the board can run,
and copies it onto the board.

1. Download **Arduino IDE 2** from <https://www.arduino.cc/en/software> and
   install it. (Used here: version 2.3.10.)
2. Open it once, then close it.

Arduino IDE includes a command-line program, `arduino-cli`, which this guide
uses. On Windows it is at:

```
%LOCALAPPDATA%\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe
```

The commands below write `arduino-cli`. Type the full path above in its place,
in quotes, or add that folder to your PATH.

## 3. Add support for the ESP32-C6 chip

Arduino IDE only knows Arduino's own boards. The XIAO ESP32C6 uses an
**Espressif ESP32-C6** chip, so you install Espressif's **esp32** package. It
contains the **RISC-V compiler** that builds programs for the ESP32-C6's
processor, Espressif's chip libraries (including Bluetooth), and the tool that
copies programs onto the board.

In a terminal, run:

```sh
arduino-cli core install esp32:esp32 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

What to expect:

- The download is about **2 GB**. The installed package takes about **6.5 GB**.
  It includes compilers for other ESP32 chips that this project does not use.
- The largest file is the RISC-V compiler, about 670 MB. Here, the download
  failed partway once (`Download failed ... connection was aborted`). Running
  the same command again finished the install.

**It worked when** `arduino-cli core list` shows `esp32:esp32` (used here:
version 3.3.12).

## 4. Put the firmware on the board

"Firmware" is the program that runs on the board. It is in
[`firmware/adaptive_controller/`](firmware/adaptive_controller/).

1. Download this repository: on GitHub, click **Code → Download ZIP** and
   unzip it. Open a terminal in the `adaptive-controller` folder.
2. Plug the XIAO into the computer.
3. Find its port:

   ```sh
   arduino-cli board list
   ```

   The board appears as a `Serial Port (USB)`, for example `COM3`.
4. Build and upload, using your port in place of `COM3`:

   ```sh
   arduino-cli compile -b esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc -u -p COM3 firmware/adaptive_controller
   ```

   `CDCOnBoot=cdc` lets the board print messages to the computer over USB.
   The first build takes a few minutes.

**It worked when** the output ends with `Hash of data verified.` and
`Hard resetting via RTS pin...`. No buttons on the board need to be pressed.

## 5. Check that it works

Install Python 3 from <https://www.python.org/downloads/>, then install the two
libraries the test scripts use:

```sh
pip install pyserial bleak
```

### 5a. Ask the board how it is

```sh
python tools/status.py COM3
```

**It worked when** you see a line like:

```
[  35686] STATUS fw=0.1.0 ble=advertising relay=off mode=idle last_off=boot battery_mv=0
```

`ble=advertising` means the board is waiting for a Bluetooth connection as
**nanoGOAT Controller**. `relay=off` means the toy output is off.

### 5b. Run the full Bluetooth test

[`tools/ble_smoke_test.py`](tools/ble_smoke_test.py) connects to the board over
the computer's Bluetooth, sends every command, and checks every safety rule it
can see from outside: a timed run ends on its own, the 60-second limit holds,
and the output turns off when the connection drops.

```sh
python tools/ble_smoke_test.py --serial COM3
```

Add `--long` to also wait out the 60-second maximum run.

**It worked when** the last line says `ALL CHECKS PASSED`. While it runs, the
orange LED turns on and off.

### 5c. Measure how fast it answers

A child's tap has to start the toy in under 500 ms
([`_specs/PRODUCT.md`](_specs/PRODUCT.md) §4a).
[`tools/latency.py`](tools/latency.py) sends 20 short runs and times each one,
from sending the command until the box reports the relay is on.

```sh
python tools/latency.py
```

Measured here, over 100 runs from a Windows 11 PC: median **57 ms**, slowest
**139 ms**. The box's own log shows each relay closing in the same millisecond
its command arrives; the rest is Bluetooth.

The box accepts **one connection at a time**. If a tool says no Adaptive
Controller was found, a phone or another program is probably connected to it.
`python tools/status.py COM3` shows `ble=connected` in that case.

## What the lights mean

| Light | Meaning |
|-------|---------|
| **Orange** on | The toy output is on. With a toy plugged in, the toy runs. |
| **Orange** off | The toy output is off. |
| **Red** | Not yet identified. |

## Problems seen so far

| Problem | What fixed it |
|---------|---------------|
| The esp32 install stopped with `Download failed` | Running the same install command again. |
| The board restarted every time a script closed its USB connection | On this chip, two USB control lines double as the reset line. The scripts in `tools/` now release them in an order that does not restart the board. A program that closes the port without doing this restarts the board; that is harmless. |

## What has not been tried yet

- Installing the board support and uploading through the Arduino IDE's
  windows and menus (this guide used the IDE's `arduino-cli`)
- The Arduino IDE Serial Monitor
- Controlling the board from a phone (for example with nRF Connect)
- Controlling the board from the nanoGOAT AAC app on a real phone or tablet
- macOS and Linux
- Wiring the relay, battery, jack, and status LED, and running a real toy
- Battery voltage measurement (the firmware reports `battery_mv=0` until the
  divider is built)

## Reference

| Path | Contents |
|------|----------|
| [`_specs/`](_specs/README.md) | What the box does and must never do. The specs are normative: if anything else disagrees with them, the spec wins. |
| [`_specs/SAFETY.md`](_specs/SAFETY.md) | Read before connecting a battery or a toy |
| [`_specs/HARDWARE.md`](_specs/HARDWARE.md) | Pins, power, jack wiring, netlist |
| [`_specs/BOM.md`](_specs/BOM.md) | Parts list |
| [`_specs/BLE_PROTOCOL.md`](_specs/BLE_PROTOCOL.md) | Bluetooth commands and status format |
| [`kicad/`](kicad/) | KiCad 10 schematic ([PDF](kicad/adaptive-controller.pdf)) |
| [`firmware/`](firmware/) | Arduino firmware |
| [`tools/`](tools/) | `status.py`, `ble_smoke_test.py`, `latency.py` |

### Edit the schematic

Install [KiCad 10](https://www.kicad.org/download/) and open
`kicad/adaptive-controller.kicad_pro`. After editing, check it and re-export.
Run these in `kicad/`. On Windows, `kicad-cli` is in
`%LOCALAPPDATA%\Programs\KiCad\10.0\bin`.

```sh
kicad-cli sch erc adaptive-controller.kicad_sch
kicad-cli sch export svg -o . adaptive-controller.kicad_sch
kicad-cli sch export pdf -o adaptive-controller.pdf adaptive-controller.kicad_sch
kicad-cli sch export netlist -o adaptive-controller.net adaptive-controller.kicad_sch
python check_netlist.py adaptive-controller.net
```

### Build phases

Each phase adds its spec to `_specs/` and stops for review.

1. Hardware design and schematic ← *in review*
2. Toy adaptation: add a 3.5mm jack to the bubble machine
3. Firmware and BLE protocol ← *runs on a bare board; Bluetooth test passes*
4. Bench test
5. Enclosure layout
