# Adaptive Controller

A small battery-powered Bluetooth box that lets the
[nanoGOAT AAC](https://nanogoat.com) app run a switch-adapted toy. A child taps
"more bubbles" on their communication board, the box closes a switch for a few
seconds, and the bubble machine runs.

The box plugs into a toy through a standard 3.5mm headphone-size jack. This is
the same plug that accessibility switches such as the AbleNet Big Red use, so
the box works with any toy that is already "switch adapted."

This guide assumes no prior experience with electronics or programming. Follow
the steps in order. Each step says how to tell that it worked.

- [1. What you need](#1-what-you-need)
- [2. Install the software](#2-install-the-software)
- [3. Put the firmware on the board](#3-put-the-firmware-on-the-board)
- [4. Check that it works](#4-check-that-it-works)
- [5. Build the box](#5-build-the-box)
- [Troubleshooting](#troubleshooting)
- [For contributors](#for-contributors)

## 1. What you need

### To try the firmware (no soldering)

| Item | Notes |
|------|-------|
| **Seeed Studio XIAO ESP32C6** | The small board that runs everything. Make sure it says **ESP32C6**; other XIAO boards need different settings. |
| **USB-C data cable** | Many USB-C cables only charge and carry no data. If your computer never sees the board, try another cable first. |
| **A computer** | Windows, macOS, or Linux, with about **8 GB of free disk space** for the tools. |
| **A phone or tablet** (optional) | For testing with the free **nRF Connect** app, or with a nanoGOAT AAC development build. |

This is enough to complete steps 2 to 4. The board's small built-in LED stands
in for the toy.

### To build the whole box

The complete parts list, with what each part does, is in
[`_specs/BOM.md`](_specs/BOM.md). You also need a soldering iron, solder, wire
strippers, and a multimeter.

## 2. Install the software

You install three things. Allow about an hour, most of it waiting for
downloads.

### 2a. Arduino IDE

Arduino IDE is the free program that turns the firmware source code into a file
the board can run, and copies that file onto the board.

1. Download **Arduino IDE 2** from <https://www.arduino.cc/en/software> and
   install it. (Tested with version 2.3.10.)
2. Open it once so it finishes its own setup.

### 2b. Support for the XIAO ESP32C6 board

Out of the box, Arduino IDE only knows Arduino's own boards. The XIAO ESP32C6
uses an **Espressif ESP32-C6** chip, so you add Espressif's free **esp32 board
package**. This package contains:

- the **RISC-V compiler** (`esp-rv32`) that builds programs for the ESP32-C6's
  processor,
- Espressif's prebuilt chip libraries, including Bluetooth, and
- `esptool`, which copies the program onto the board.

It also installs compilers for other ESP32 chips that this project does not
use. The download is about 2 GB, and the installed package takes about
**6.5 GB**. You do this once per computer.

1. In Arduino IDE, open **File → Preferences** (on macOS: **Arduino IDE →
   Settings**).
2. In **Additional boards manager URLs**, paste:

   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```

   Click **OK**.
3. Open **Tools → Board → Boards Manager**.
4. Search for **esp32**. Find **esp32 by Espressif Systems** (not "Arduino
   ESP32 Boards") and click **Install**. (Tested with version 3.3.12.)
5. Wait. The progress bar can sit on one large file for many minutes. If the
   download fails partway, click **Install** again.

**It worked when** **Tools → Board → esp32** lists **XIAO_ESP32C6**.

This is the same setup Seeed describes on the
[XIAO ESP32C6 getting-started page](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/).

### 2c. Get this project

Download this repository to your computer:

- **Without git:** on the GitHub page, click **Code → Download ZIP**, then
  unzip it.
- **With git:** `git clone https://github.com/dstadelman/nanoGOAT-adaptive-devices.git`

## 3. Put the firmware on the board

"Firmware" is the program that runs on the board. It lives in
[`firmware/adaptive_controller/adaptive_controller.ino`](firmware/adaptive_controller/adaptive_controller.ino).

1. Plug the XIAO into your computer with the USB-C cable.
2. In Arduino IDE, open **File → Open** and choose
   `adaptive-controller/firmware/adaptive_controller/adaptive_controller.ino`.
3. Choose the board: **Tools → Board → esp32 → XIAO_ESP32C6**.
4. Turn on USB logging: **Tools → USB CDC On Boot → Enabled**. Without this,
   the board runs but prints nothing to your computer.
5. Choose the port: **Tools → Port**, then pick the new entry that appeared
   when you plugged in the board:
   - Windows: `COM3`, `COM4`, or similar
   - macOS: `/dev/cu.usbmodem…`
   - Linux: `/dev/ttyACM0`
6. Click **Upload** (the right-arrow button). The first build takes a few
   minutes; later builds are faster.

**It worked when** the output panel ends with `Hash of data verified.` and
`Hard resetting via RTS pin...`.

## 4. Check that it works

### 4a. Watch the board's log

1. Open **Tools → Serial Monitor** and set the speed to **115200 baud**.
2. Press the tiny **Reset** button on the XIAO. (It has two buttons, **BOOT**
   and **Reset**; see the photo on Seeed's getting-started page.)

You see lines like these:

```
[    312] BOOT fw=0.1.0 proto=1 battery_sense=0
[    420] ADV start
```

`ADV start` means the board is advertising over Bluetooth as
**nanoGOAT Controller**. The board only prints when something happens, so a
quiet Serial Monitor after that is normal.

### 4b. Run the toy from a phone (nRF Connect)

**nRF Connect for Mobile** is a free app from Nordic Semiconductor for talking
to Bluetooth devices. It is on the App Store and Google Play.

1. Open nRF Connect and tap **Scan**.
2. Find **nanoGOAT Controller** and tap **Connect**.
3. Open the service that starts with `54ce0001`.
4. On the characteristic that starts with `54ce0002`, tap the **up arrow**
   (write). Choose the byte array format and enter `0188130000`. Tap **Send**.

**It worked when** the small orange LED on the XIAO lights for 5 seconds and
then turns off by itself. The Serial Monitor shows `RELAY ON` and then
`RELAY OFF reason=timer`.

`0188130000` means "run for 5000 milliseconds." All commands are listed in
[`_specs/BLE_PROTOCOL.md`](_specs/BLE_PROTOCOL.md).

### 4c. Run the full test from a computer (optional)

[`tools/ble_smoke_test.py`](tools/ble_smoke_test.py) connects over your
computer's Bluetooth, tries every command, and checks every safety rule it can
observe: the timer ends a run, the 60-second limit holds, and the box stops
when the connection drops.

1. Install [Python 3](https://www.python.org/downloads/).
2. Close the Arduino Serial Monitor, because only one program can use the port.
3. Run, from the `adaptive-controller` folder:

   ```sh
   pip install bleak pyserial
   python tools/ble_smoke_test.py --serial COM3
   ```

   Use your own port name in place of `COM3`. Add `--long` to also wait out the
   60-second maximum run.

**It worked when** the last line says `ALL CHECKS PASSED`.

### 4d. Run it from nanoGOAT AAC

The nanoGOAT AAC app has a hidden test screen for the box. It exists only in
development builds. Maintainers: see
[`nanoGOAT-aac-app/_specs/ADAPTIVE_CONTROLLER.md`](https://github.com/dstadelman/nanoGOAT-aac-app/blob/main/_specs/ADAPTIVE_CONTROLLER.md).

## 5. Build the box

The electrical design is in [`_specs/HARDWARE.md`](_specs/HARDWARE.md). It
covers which pin connects where, how power flows, and how to identify the
jack's terminals with a multimeter. The schematic is
[`kicad/adaptive-controller.pdf`](kicad/adaptive-controller.pdf).

Read [`_specs/SAFETY.md`](_specs/SAFETY.md) before you connect a battery or a
toy. In short:

- Use battery-powered toys only. Never connect the box to anything that plugs
  into a wall outlet.
- Check the battery connector's polarity with a multimeter before connecting
  it. JST battery connectors are not wired the same way by every seller.

Step-by-step build guides (adapting the bubble machine, soldering the box, the
enclosure) are in progress. See [Build phases](#build-phases).

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| The esp32 download stops or fails | Click **Install** again. The largest file (the RISC-V compiler) is several hundred MB, and a slow connection can drop it. |
| No new port appears under **Tools → Port** | Try a different USB-C cable; charge-only cables are common. Try a different USB port. |
| Upload fails with "No serial data received" or "Failed to connect" | Put the board in download mode: unplug it, hold the **BOOT** button, plug the USB cable back in while still holding **BOOT**, then release it. Click **Upload** again. Press **Reset** afterward to run the new firmware. |
| Serial Monitor shows nothing | Check **USB CDC On Boot → Enabled** and re-upload. Set the speed to 115200. Press **Reset** to see the boot lines. |
| Serial Monitor shows garbled characters | Set the speed to **115200**. |
| The phone cannot find **nanoGOAT Controller** | Make sure the board is powered and the Serial Monitor showed `ADV start`. The box accepts one connection at a time, so disconnect any other phone or computer. |
| The test script cannot open the port | Close the Arduino Serial Monitor first. |
| Linux: permission denied on `/dev/ttyACM0` | Add yourself to the `dialout` group (`sudo usermod -aG dialout $USER`), then log out and back in. |

## For contributors

### Folder map

| Path | Contents |
|------|----------|
| [`_specs/`](_specs/README.md) | What the box does and must never do. The specs are normative: if anything else disagrees with them, the spec wins. |
| [`kicad/`](kicad/) | KiCad 10 schematic project |
| [`firmware/`](firmware/) | Arduino firmware |
| [`tools/`](tools/) | PC-side test script |

### Build from the command line

`arduino-cli` is the command-line engine inside Arduino IDE. It is also
available on its own from <https://arduino.github.io/arduino-cli/>.

```sh
arduino-cli core install esp32:esp32 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli compile -b esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc -u -p COM3 firmware/adaptive_controller
```

### Edit the schematic

Install [KiCad 10](https://www.kicad.org/download/), open
`kicad/adaptive-controller.kicad_pro`, and double-click the schematic. The
project symbols (XIAO ESP32C6, relay module) are in
`kicad/adaptive-controller.kicad_sym`. After editing, re-export the SVG and PDF
and check the netlist against HARDWARE §7. Run these in `kicad/`:

```sh
kicad-cli sch erc adaptive-controller.kicad_sch
kicad-cli sch export svg -o . adaptive-controller.kicad_sch
kicad-cli sch export pdf -o adaptive-controller.pdf adaptive-controller.kicad_sch
kicad-cli sch export netlist -o adaptive-controller.net adaptive-controller.kicad_sch
python check_netlist.py adaptive-controller.net
```

On Windows, `kicad-cli` is in KiCad's `bin` folder, for example
`%LOCALAPPDATA%\Programs\KiCad\10.0\bin`.

### Build phases

Each phase adds its spec to `_specs/` and stops for review.

1. Hardware design and schematic ← *in review*
2. Toy adaptation: add a 3.5mm jack to the bubble machine
3. Firmware and BLE protocol ← *running on a bare XIAO; BLE checks pass*
4. Bench test (verifiable from serial logs)
5. Enclosure layout
