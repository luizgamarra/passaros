"""Read a bounded serial log, optionally resetting ESP32 through its UART bridge."""
import argparse
import re
import time
from pathlib import Path
import serial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True)
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--output', type=Path, default=Path('results/hardware/serial.log'))
    parser.add_argument('--reset', action='store_true')
    parser.add_argument('--pause', action='store_true')
    args = parser.parse_args()
    device = serial.Serial(port=None, baudrate=115200, timeout=0.2)
    device.dtr = False; device.rts = False; device.port = args.port
    collected = bytearray()
    with device:
        if args.reset:
            device.dtr = False
            device.rts = True
            time.sleep(0.1)
            device.rts = False
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            collected.extend(device.read(max(1, device.in_waiting)))
        if args.pause:
            device.write(b'p')
    decoded = collected.decode('utf-8', errors='replace')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(decoded, encoding='utf-8')
    print(re.sub(r'\x1b\[[0-9;]*m', '', decoded))


if __name__ == '__main__':
    main()
