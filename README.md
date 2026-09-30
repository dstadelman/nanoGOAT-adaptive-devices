# nanoGOAT Adaptive Devices

Open hardware that connects the [nanoGOAT AAC](https://nanogoat.com) app to the
physical world. Everything here is low-voltage, battery-powered, and built from
off-the-shelf parts so it can be reproduced at a kitchen table.

> **New here? Start with the [Adaptive Controller guide](adaptive-controller/README.md).**
> It takes you from nothing installed to a XIAO ESP32C6 board you can control
> over Bluetooth, and says which steps have not been tried yet.

Devices fall into two directions:

| Direction | Device | What it does | Status |
|-----------|--------|--------------|--------|
| **Output** (app → world) | [`adaptive-controller/`](adaptive-controller/) | A Bluetooth box with a 3.5mm jack. The app tells it to close a relay, which runs any switch-adapted toy (first up: a bubble machine). | Firmware works on a bare board; box build in progress |
| **Input** (world → app) | [`switch-interface/`](switch-interface/) | Lets a standard accessibility switch (e.g. a Big Red button) drive the tablet for switch scanning. | Idea |

## Vocabulary

- **Accessibility switch** (or *adaptive switch*): the big, easy-to-press button
  a person uses, e.g. AbleNet Big Red or Jelly Bean. It is just a momentary
  contact on a 3.5mm mono plug.
- **Switch-adapted toy**: a battery toy with a 3.5mm mono jack wired across its
  on/off switch. Shorting tip to sleeve runs the toy.
- **Switch interface**: a box that turns switch presses into input a tablet
  understands.

## Safety

Low voltage and battery toys only. Nothing mains-powered, ever.

## License

MIT, see [LICENSE](LICENSE).
