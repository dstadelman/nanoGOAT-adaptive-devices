# `_specs` — Adaptive Controller specifications

**This folder is normative.** If firmware, wiring, issues, or videos disagree
with a spec, the spec wins. Fix the build or change the spec first.

## Folder laws

1. **Spec before build.** A behavior or wiring change starts as a spec edit,
   then an issue, then the build.
2. **Present tense only.** Specs describe what is true. No changelogs,
   strike-throughs, or "used to be." History lives in git and issues.
3. **One owner per fact.** Each fact has one spec. Other specs link to it
   instead of restating it.
4. **Issues name gaps.** Specs state the desired law. Issues state where the
   physical build or firmware diverges.

## Specs in this folder

| Spec | Owns |
|------|------|
| [PRODUCT](PRODUCT.md) | Goal, users, operating modes, status LED meanings, how the box is used day to day |
| [SAFETY](SAFETY.md) | Safety invariants that every other spec, the firmware and the wiring obey |
| [HARDWARE](HARDWARE.md) | Pin assignments, power path, current budget, output jack, netlist |
| [BOM](BOM.md) | Parts list and procurement status |
| [BLE_PROTOCOL](BLE_PROTOCOL.md) | GATT service, commands, and status format: the app ↔ box contract |
| [FIRMWARE](FIRMWARE.md) | Platform, timing values, state machine, indicators, serial log |

Specs still to come, one per build phase: toy adaptation (bubble machine),
bench test, enclosure.

## Precedence

| Domain | Winner |
|--------|--------|
| Anything that can leave a toy running or hurt someone | SAFETY |
| What the user sees and does | PRODUCT |
| What is wired to what | HARDWARE |
| Bytes between app and box | BLE_PROTOCOL |
| Timing values and firmware behavior | FIRMWARE |
| What to buy | BOM |

The KiCad schematic in [`../kicad/`](../kicad/) follows HARDWARE. If the two
disagree, HARDWARE wins.
