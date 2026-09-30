"""Drives an Adaptive Controller over BLE and checks every rule it can observe.

    pip install bleak pyserial
    python ble_smoke_test.py                 # BLE checks only
    python ble_smoke_test.py --serial COM3   # also prints the box's serial log
    python ble_smoke_test.py --long          # adds the 60 s maximum on-time check

Checks the wire format in ../_specs/BLE_PROTOCOL.md and the off rules in
../_specs/SAFETY.md §2. Relay state is read only from STATE, never assumed.
"""
import argparse
import asyncio
import struct
import sys
import threading
import time

from bleak import BleakClient, BleakScanner

SERVICE = "54ce0001-eae9-4eb4-8f51-34fbe6573f4c"
CONTROL = "54ce0002-eae9-4eb4-8f51-34fbe6573f4c"
STATE = "54ce0003-eae9-4eb4-8f51-34fbe6573f4c"

MODES = ["idle", "timed", "latched", "direct"]
REASONS = ["boot", "command", "timer", "max_on", "heartbeat", "disconnect",
           "low_battery", "error"]

RUN_TIMED = lambda ms: struct.pack("<BI", 0x01, ms)
RUN_LATCHED = bytes([0x02])
OFF = bytes([0x03])
TOGGLE = bytes([0x04])
HOLD = bytes([0x05])
SET_DEFAULT = lambda ms: struct.pack("<BI", 0x10, ms)

T0 = time.monotonic()
failures = []


def log(tag, msg):
    print(f"{time.monotonic() - T0:7.2f}  {tag:6} {msg}", flush=True)


def parse(value):
    (ver, relay, mode, reason, remaining, mv, default_ms, hb_ms, max_s) = \
        struct.unpack("<BBBBIHIHB", bytes(value))
    return dict(version=ver, relay=bool(relay), mode=MODES[mode],
                reason=REASONS[reason], remaining=remaining, battery_mv=mv,
                default_ms=default_ms, heartbeat_ms=hb_ms, max_on_s=max_s)


def check(name, ok, detail=""):
    log("PASS" if ok else "FAIL", f"{name} {detail}".rstrip())
    if not ok:
        failures.append(name)


def tail_serial(port, stop):
    import serial
    try:
        s = serial.Serial(port, 115200, timeout=0.2)
    except Exception as e:  # noqa: BLE001 - report and carry on without logs
        log("SERIAL", f"not opened: {e}")
        return
    while not stop.is_set():
        line = s.readline()
        if line:
            log("BOX", line.decode(errors="replace").rstrip())
    # RTS/DTR double as the ESP32-C6 reset line; a plain close restarts the box.
    s.rts = False
    s.dtr = False
    s.close()


class Box:
    def __init__(self, client):
        self.client = client
        self.state = None
        self.changed = asyncio.Event()

    async def start(self):
        await self.client.start_notify(STATE, self._on_state)
        self.state = parse(await self.client.read_gatt_char(STATE))

    def _on_state(self, _, value):
        self.state = parse(value)
        self.changed.set()

    async def send(self, data, response=True):
        await self.client.write_gatt_char(CONTROL, data, response=response)

    async def wait_for(self, predicate, timeout):
        end = time.monotonic() + timeout
        while not predicate(self.state):
            left = end - time.monotonic()
            if left <= 0:
                return False
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), left)
            except asyncio.TimeoutError:
                return predicate(self.state)
        return True


async def find():
    log("BLE", "scanning for the controller service…")
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: SERVICE in [u.lower() for u in adv.service_uuids],
        timeout=10)
    if device is None:
        log("FAIL", "no Adaptive Controller found")
        sys.exit(1)
    log("BLE", f"found {device.name} {device.address}")
    return device


async def run(long_test):
    device = await find()

    async with BleakClient(device) as client:
        box = Box(client)
        await box.start()
        s = box.state
        log("STATE", s)
        check("protocol version is 1", s["version"] == 1)
        check("relay off after connect", not s["relay"])

        # Timed run ends by itself.
        await box.send(RUN_TIMED(2000))
        check("RUN_TIMED 2 s turns relay on",
              await box.wait_for(lambda s: s["relay"] and s["mode"] == "timed", 2))
        check("timed run ends on its own",
              await box.wait_for(lambda s: not s["relay"], 3.5))
        check("off reason is timer", box.state["reason"] == "timer",
              box.state["reason"])

        # Latched run ends on OFF.
        await box.send(RUN_LATCHED)
        check("RUN_LATCHED turns relay on",
              await box.wait_for(lambda s: s["relay"] and s["mode"] == "latched", 2))
        await asyncio.sleep(1)
        await box.send(OFF)
        check("OFF turns relay off", await box.wait_for(lambda s: not s["relay"], 2))
        check("off reason is command", box.state["reason"] == "command")

        # TOGGLE twice.
        await box.send(TOGGLE)
        check("TOGGLE on", await box.wait_for(lambda s: s["relay"], 2))
        await box.send(TOGGLE)
        check("TOGGLE off", await box.wait_for(lambda s: not s["relay"], 2))

        # Direct mode: on while HOLD arrives, off when it stops.
        for _ in range(6):
            await box.send(HOLD, response=False)
            await asyncio.sleep(0.5)
        check("HOLD keeps relay on", box.state["relay"] and box.state["mode"] == "direct")
        stopped = time.monotonic()
        check("relay off after heartbeats stop",
              await box.wait_for(lambda s: not s["relay"], 3))
        lapse = time.monotonic() - stopped
        check("off reason is heartbeat", box.state["reason"] == "heartbeat",
              f"after {lapse:.2f} s")

        # Malformed command is ignored.
        await box.send(bytes([0x01, 0x10]))
        await box.send(bytes([0x7F]))
        await asyncio.sleep(0.5)
        check("malformed commands leave relay off", not box.state["relay"])

        # Stored default duration round-trips.
        await box.send(SET_DEFAULT(3000))
        check("SET_DEFAULT_DURATION 3 s",
              await box.wait_for(lambda s: s["default_ms"] == 3000, 2))
        await box.send(SET_DEFAULT(5000))
        await box.wait_for(lambda s: s["default_ms"] == 5000, 2)

        # Clamp: a request longer than the maximum is capped.
        await box.send(RUN_TIMED(600_000))
        await box.wait_for(lambda s: s["relay"], 2)
        cap = box.state["max_on_s"] * 1000
        check("RUN_TIMED is clamped to max on-time",
              box.state["remaining"] <= cap, f"remaining={box.state['remaining']}")
        if long_test:
            check("max on-time ends the run",
                  await box.wait_for(lambda s: not s["relay"], cap / 1000 + 3))
            check("off reason is max_on", box.state["reason"] == "max_on")
        else:
            await box.send(OFF)
            await box.wait_for(lambda s: not s["relay"], 2)

        # Disconnect while running.
        await box.send(RUN_LATCHED)
        check("running before disconnect", await box.wait_for(lambda s: s["relay"], 2))
        log("BLE", "disconnecting while the relay is on")

    await asyncio.sleep(2)
    device = await find()
    async with BleakClient(device) as client:
        box = Box(client)
        await box.start()
        check("relay off after disconnect", not box.state["relay"])
        check("off reason is disconnect", box.state["reason"] == "disconnect",
              box.state["reason"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", help="serial port for the box's log, e.g. COM3")
    ap.add_argument("--long", action="store_true", help="include the 60 s max on-time check")
    args = ap.parse_args()

    stop = threading.Event()
    reader = None
    if args.serial:
        reader = threading.Thread(target=tail_serial, args=(args.serial, stop), daemon=True)
        reader.start()
        time.sleep(0.5)
    try:
        asyncio.run(run(args.long))
    finally:
        time.sleep(0.5)
        stop.set()
        if reader:
            reader.join(timeout=2)  # let it release the port without resetting the box

    print()
    if failures:
        print(f"FAILED {len(failures)}: {', '.join(failures)}")
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
