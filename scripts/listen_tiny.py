"""Listen to the PC microphone using the ESP32 baseline's exact INT8 model."""
import argparse
import json
from math import gcd

import numpy as np
import sounddevice as sd
from ai_edge_litert.interpreter import Interpreter
from scipy.signal import resample_poly

from infer_tiny import ROOT, FeatureHandler


def device_argument(value):
    return int(value) if value.isdecimal() else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-devices', action='store_true')
    parser.add_argument('--device', type=device_argument, help='ID ou nome do microfone')
    parser.add_argument('--windows', type=int, default=0, help='Limite de blocos; 0 escuta ate Ctrl+C')
    args = parser.parse_args()
    if args.list_devices:
        print(sd.query_devices())
        return
    if args.windows < 0:
        parser.error('--windows deve ser >= 0')
    device = sd.query_devices(args.device, 'input')
    rate = int(device['default_samplerate'])
    sd.check_input_settings(device=args.device, channels=1, dtype='int16', samplerate=rate)
    labels = json.loads((ROOT / 'models/labels.json').read_text(encoding='utf-8'))
    interpreter = Interpreter(model_content=(ROOT / 'firmware/main/model.tflite').read_bytes(), num_threads=1)
    interpreter.allocate_tensors()
    input_info = interpreter.get_input_details()[0]
    output_info = interpreter.get_output_details()[0]
    if input_info['shape'].tolist() != [1, 1, 40, 133] or input_info['dtype'] != np.int8:
        raise ValueError('Modelo incompativel com o DSP baseline')
    if output_info['shape'].tolist() != [1, len(labels)]:
        raise ValueError('Labels incompativeis com o modelo')
    scale, zero = input_info['quantization']
    output_scale, _ = output_info['quantization']
    handler = FeatureHandler(add_batch_dimension=True)
    handler.extract(np.arange(72000, dtype=np.int16))
    factor = gcd(rate, 24000)
    print(f'Microfone: {device["name"]} | captura={rate} Hz | modelo=24000 Hz', flush=True)
    print('Escutando blocos de 3 segundos. De play no canto pelo alto-falante. Ctrl+C encerra.', flush=True)
    count = 0
    try:
        with sd.InputStream(device=args.device, samplerate=rate, channels=1,
                            dtype='int16', latency='high') as stream:
            while args.windows == 0 or count < args.windows:
                recorded, overflow = stream.read(rate * 3)
                count += 1
                if overflow:
                    print('Captura perdeu amostras; descartando este bloco.', flush=True)
                    continue
                pcm = recorded[:, 0]
                if rate != 24000:
                    converted = resample_poly(pcm.astype(np.float64), 24000 // factor, rate // factor)
                    pcm = np.clip(np.rint(converted), -32768, 32767).astype(np.int16)
                if pcm.shape != (72000,):
                    raise ValueError('Captura nao produziu 72000 amostras')
                rms = float(np.sqrt(np.mean(pcm.astype(np.float64) ** 2)))
                if rms < 8:
                    print(f'Audio quase nulo rms={rms:.1f}: confira microfone e volume.', flush=True)
                    continue
                features = handler.extract(pcm)
                if not np.isfinite(features).all():
                    raise ValueError('Features nao finitas')
                tensor = np.clip(features / scale + zero, -128, 127).astype(np.int8)
                interpreter.set_tensor(input_info['index'], tensor)
                interpreter.invoke()
                output = interpreter.get_tensor(output_info['index'])[0]
                index = int(np.argmax(output))
                scores = np.exp((output.astype(np.float64) - int(output[index])) * output_scale)
                score = float(scores[index] / scores.sum())
                peak = int(np.abs(pcm.astype(np.int32)).max())
                clipped = int(np.count_nonzero((pcm == -32768) | (pcm == 32767)))
                print(f'classe={labels[index]} score_relativo={score:.3f} rms={rms:.1f} pico={peak} clipping={clipped}', flush=True)
    except KeyboardInterrupt:
        print('\nEscuta encerrada.', flush=True)


if __name__ == '__main__':
    main()
