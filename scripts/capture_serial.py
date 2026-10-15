"""Export one three-second PCM clip from the firmware, without a network server."""
import argparse
import time
import wave
from pathlib import Path
import serial


def capture(port, destination):
    device = serial.Serial(port=None, baudrate=115200, timeout=0.5)
    device.dtr = False
    device.rts = False
    device.port = port
    with device:
        device.reset_input_buffer()
        device.write(b'p')
        time.sleep(4)
        device.reset_input_buffer()
        device.write(b'a')
        deadline = time.monotonic() + 40
        header = b''
        while time.monotonic() < deadline:
            header = device.readline()
            if header.startswith(b'PCM_BEGIN '):
                break
        else:
            raise RuntimeError('PCM_BEGIN ausente: confira UART/porta e microfone')
        parts = header.split()
        length, rate = int(parts[1]), int(parts[2])
        if length != 144000 or rate != 24000:
            raise RuntimeError(f'Contrato PCM inesperado: {header!r}')
        data = bytearray()
        while len(data) < length and time.monotonic() < deadline:
            data.extend(device.read(length - len(data)))
        if len(data) != length:
            raise RuntimeError(f'Captura truncada: {len(data)}/{length}')
        if device.readline().strip() != b'':
            raise RuntimeError('Fim de payload inesperado')
        if device.readline().strip() != b'PCM_END':
            raise RuntimeError('PCM_END ausente; descarte a captura')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(data)
    print(f'WAV salvo: {destination}; placa pausada, comando m retoma a captura')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', required=True)
    parser.add_argument('--output', type=Path, default=Path('data/microfone.wav'))
    args = parser.parse_args()
    capture(args.port, args.output)
