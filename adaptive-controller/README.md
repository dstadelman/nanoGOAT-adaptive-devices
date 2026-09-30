# Adaptive Controller

A battery-powered Bluetooth box that lets the nanoGOAT AAC app run any
switch-adapted toy. A child taps "more bubbles" on their AAC board, the box
closes a relay for a few seconds, and the bubble machine runs.

- **What it is and how it behaves:** [`_specs/`](_specs/README.md)
- **Schematic:** [`kicad/`](kicad/), a KiCad 10 project. Open
  `kicad/adaptive-controller.kicad_pro` in KiCad and double-click the
  schematic. Project symbols (XIAO ESP32C6, relay module) live in
  `kicad/adaptive-controller.kicad_sym`. After editing, re-export the SVG and
  PDF and re-check the netlist against HARDWARE §7 (run in `kicad/`; add
  kicad-cli's folder to your PATH or use its full path):

  ```sh
  kicad-cli sch erc adaptive-controller.kicad_sch
  kicad-cli sch export svg -o . adaptive-controller.kicad_sch
  kicad-cli sch export pdf -o adaptive-controller.pdf adaptive-controller.kicad_sch
  kicad-cli sch export netlist -o adaptive-controller.net adaptive-controller.kicad_sch
  python check_netlist.py adaptive-controller.net
  ```

- **Firmware:** [`firmware/adaptive_controller/`](firmware/adaptive_controller/).
  Arduino IDE: install the **esp32** board package by Espressif, pick board
  **XIAO_ESP32C6**, set *USB CDC On Boot* to *Enabled*, and upload. Or:

  ```sh
  arduino-cli compile -b esp32:esp32:XIAO_ESP32C6:CDCOnBoot=cdc -u -p COM3 firmware/adaptive_controller
  ```

- **BLE test from a PC:** [`tools/ble_smoke_test.py`](tools/ble_smoke_test.py)
  drives every command and checks every off rule it can observe
  (`pip install bleak pyserial`, then
  `python tools/ble_smoke_test.py --serial COM3`; add `--long` for the 60 s
  maximum on-time check).

## Build phases

Each phase adds its spec to `_specs/` and stops for review.

1. Hardware design and schematic ← *in review*
2. Toy adaptation: add a 3.5mm jack to the bubble machine
3. Firmware and BLE protocol ← *running on a bare XIAO; BLE checks pass*
4. Bench test (verifiable from serial logs)
5. Enclosure layout
