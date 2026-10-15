"""Run the ESP32's exact INT8 model on WAV files, without changing firmware."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import soundfile as sf
from ai_edge_litert.interpreter import Interpreter

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream/BioDCASE-Tiny-2026'
sys.path.insert(0, str(UPSTREAM))
from feature_handler import FeatureHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, help='WAV de 3 s, mono, 24 kHz, PCM 16 bits')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/tiny_python.csv')
    args = parser.parse_args()
    paths = [args.audio] if args.audio else sorted(
        (UPSTREAM / 'submission/test_wav_files').rglob('*.wav'))
    if not paths:
        parser.error('Nenhum WAV encontrado')
    model_path = ROOT / 'firmware/main/model.tflite'
    model_bytes = model_path.read_bytes()
    labels = json.loads((ROOT / 'models/labels.json').read_text(encoding='utf-8'))
    interpreter = Interpreter(model_content=model_bytes, num_threads=1)
    interpreter.allocate_tensors()
    input_info = interpreter.get_input_details()[0]
    output_info = interpreter.get_output_details()[0]
    if input_info['shape'].tolist() != [1, 1, 40, 133] or input_info['dtype'] != np.int8:
        raise ValueError('Modelo nao corresponde ao contrato do DSP baseline')
    if output_info['shape'].tolist() != [1, len(labels)]:
        raise ValueError('Labels nao correspondem a saida do modelo')
    handler = FeatureHandler(add_batch_dimension=True)
    scale, zero = input_info['quantization']
    output_scale, output_zero = output_info['quantization']
    rows = []
    for path in paths:
        info = sf.info(path)
        if (info.samplerate, info.channels, info.frames, info.subtype) != (24000, 1, 72000, 'PCM_16'):
            raise ValueError(f'{path}: esperado WAV de 3 s, mono, 24 kHz, PCM_16; recebido {info}')
        pcm, _ = sf.read(path, dtype='int16')
        started = perf_counter()
        features = handler.extract(pcm) if np.any(pcm) else np.zeros((1, 1, 40, 133), np.float32)
        if not np.isfinite(features).all():
            raise ValueError(f'{path}: features nao finitas')
        tensor = np.clip(features / scale + zero, -128, 127).astype(np.int8)
        preprocessed = perf_counter()
        interpreter.set_tensor(input_info['index'], tensor)
        interpreter.invoke()
        finished = perf_counter()
        output = interpreter.get_tensor(output_info['index'])[0]
        logits = (output.astype(np.float64) - output_zero) * output_scale
        scores = np.exp(logits - logits.max())
        scores /= scores.sum()
        index = int(np.argmax(output))
        expected = '' if args.audio else path.parent.name
        row = {'file': str(path.resolve()), 'expected': expected, 'predicted': labels[index],
               'score_relativo': round(float(scores[index]), 6),
               'DSP_ms_PC': round((preprocessed - started) * 1000, 3),
               'ML_ms_PC': round((finished - preprocessed) * 1000, 3)}
        rows.append(row)
        status = 'OK' if expected == labels[index] else 'ERRO' if expected else 'RESULTADO'
        print(f"{status}: esperado={expected or '?'} | classe={labels[index]} | score_relativo={scores[index]:.3f}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {'model': str(model_path), 'model_sha256': hashlib.sha256(model_bytes).hexdigest(),
              'total': len(rows), 'correct': None if args.audio else sum(
                  row['expected'] == row['predicted'] for row in rows),
              'csv': str(args.output.resolve()),
              'note': 'Bundled examples are execution checks, not field accuracy. PC timings do not measure ESP32 performance.'}
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
