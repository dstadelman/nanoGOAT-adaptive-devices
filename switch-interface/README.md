# Switch Interface (idea, not started)

The input direction: a person presses an accessibility switch, and the tablet
treats it as a scanning input.

## Notes to resolve before designing

- **Where scanning lives.** Android (Switch Access) and iOS/iPadOS (Switch
  Control) both do switch scanning at the OS level. They accept a Bluetooth
  keyboard as the switch source. A box that shows up as a BLE HID keyboard and
  sends one key per switch press would then work with any app, with no app
  changes. The catch is that OS scanning only reaches controls the app exposes
  to the accessibility tree.
- **In-app scanning.** No switch-scanning code was found in `nanoGOAT-aac-app`
  as of 2026-09-30. If in-app scanning is wanted (it can be tuned for AAC grids),
  it's an app feature, and this box would still just be a keyboard.
- **Hardware overlap.** The same XIAO ESP32C6 plus a 3.5mm jack *input* (no
  relay) likely covers it. Two jacks give two-switch scanning (move + select).
