"""Asks the board for one STATUS line over USB and prints what it says.

    pip install pyserial
    python status.py COM3

Any input makes the firmware print a STATUS line (../_specs/FIRMWARE.md §6).
"""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM3"
s = serial.Serial(port, 115200, timeout=0.3)
time.sleep(0.3)
s.reset_input_buffer()
s.write(b"s")
end = time.time() + 3
while time.time() < end:
    line = s.readline()
    if line:
        print(line.decode(errors="replace").rstrip())
# On the ESP32-C6's built-in USB, RTS and DTR double as the reset line. A plain
# close restarts the board; releasing RTS before DTR does not.
s.rts = False
s.dtr = False
s.close()
