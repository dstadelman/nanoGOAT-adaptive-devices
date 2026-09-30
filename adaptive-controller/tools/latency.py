"""Measures how fast the box answers a command over BLE from this computer.

    pip install bleak
    python latency.py            # 20 runs
    python latency.py -n 50

For each run it sends RUN_TIMED 300 ms and times two things:
  write done   - the box acknowledged the write
  relay on     - the STATE notification says the relay is on
The second number is the whole round trip seen from this computer: command
out, box closes the relay, status back. The box's own share is under a few ms
(see its serial log); the rest is Bluetooth. Limits: ../_specs/PRODUCT.md §4a.
"""
import argparse
import asyncio
import statistics
import struct
import time

from bleak import BleakClient, BleakScanner

SERVICE = "54ce0001-eae9-4eb4-8f51-34fbe6573f4c"
CONTROL = "54ce0002-eae9-4eb4-8f51-34fbe6573f4c"
STATE = "54ce0003-eae9-4eb4-8f51-34fbe6573f4c"


async def main(n):
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: SERVICE in [u.lower() for u in adv.service_uuids], timeout=10)
    if device is None:
        raise SystemExit("No Adaptive Controller found. Is another phone or app connected to it?")

    async with BleakClient(device) as client:
        # Timestamp every STATE notification as it arrives, so a quick
        # on-then-off pair can never be missed.
        events = []  # (time, relay_on)

        def on_state(_, value):
            events.append((time.perf_counter(), value[1] == 1))

        await client.start_notify(STATE, on_state)
        acked, seen = [], []
        for i in range(n):
            events.clear()
            t0 = time.perf_counter()
            await client.write_gatt_char(CONTROL, struct.pack("<BI", 0x01, 300), response=True)
            t1 = time.perf_counter()
            deadline = t0 + 3
            while not any(on for _, on in events) and time.perf_counter() < deadline:
                await asyncio.sleep(0.002)
            on_times = [t for t, on in events if on]
            if not on_times:
                raise SystemExit(f"run {i + 1}: no relay-on status within 3 s")
            acked.append((t1 - t0) * 1000)
            seen.append((on_times[0] - t0) * 1000)
            await asyncio.sleep(0.6)  # let the 300 ms run end

    def summary(xs):
        xs = sorted(xs)
        return (f"median {statistics.median(xs):4.0f} ms   "
                f"p90 {xs[int(len(xs) * 0.9) - 1]:4.0f} ms   max {xs[-1]:4.0f} ms")

    print(f"runs: {n}")
    print(f"write done : {summary(acked)}")
    print(f"relay on   : {summary(seen)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=20)
    asyncio.run(main(ap.parse_args().n))
