"""Prepare an offline ESP32-S3 example from the official BioDCASE baseline."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import yaml
from ai_edge_litert.interpreter import Interpreter

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'upstream/BioDCASE-Tiny-2026'
sys.path.insert(0, str(UPSTREAM))
from feature_handler import FeatureHandler
from biodcase_tiny.feature_extraction.feature_extraction import convert_constants


def features(audio, handler, detail):
    if len(audio) != 72000 or audio.dtype != np.int16:
        raise ValueError('Expected 72000 mono int16 samples at 24000 Hz')
    extracted = handler.extract(audio)
    if not np.isfinite(extracted).all():
        raise ValueError('Feature extraction returned non-finite values')
    scale, zero = detail['quantization']
    return np.clip(extracted / scale + zero, -128, 127).astype(np.int8)


def main():
    source = UPSTREAM / 'submission/your_submission_model/test_Baseline.tflite'
    destination = ROOT / 'models/biodcase_baseline.tflite'
    shutil.copyfile(source, destination)
    label_source = UPSTREAM / 'submission/your_submission_model/label_dict.yaml'
    mapping = yaml.safe_load(label_source.read_text())['label_dict']
    labels = [name for name, index in sorted(mapping.items(), key=lambda item: item[1])]
    (ROOT / 'models/labels.json').write_text(json.dumps(labels, indent=2), encoding='utf-8')
    interpreter = Interpreter(model_content=destination.read_bytes(), num_threads=1)
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    assert input_detail['shape'].tolist() == [1, 1, 40, 133]
    assert input_detail['dtype'] == np.int8
    handler = FeatureHandler(add_batch_dimension=True)
    rows = []
    for wav in sorted((UPSTREAM / 'submission/test_wav_files').rglob('*.wav')):
        audio, rate = sf.read(wav, dtype='int16')
        assert rate == 24000 and audio.ndim == 1
        tensor = features(audio, handler, input_detail)
        interpreter.set_tensor(input_detail['index'], tensor)
        interpreter.invoke()
        output = interpreter.get_tensor(output_detail['index'])[0]
        index = int(np.argmax(output))
        rows.append({'audio': str(wav.relative_to(UPSTREAM)), 'actual': wav.parent.name,
                     'predicted': labels[index], 'output_int8': output.tolist()})
        if wav.parent.name == 'Eurasian Blackbird':
            (ROOT / 'firmware/main/reference_audio.pcm').write_bytes(audio.astype('<i2').tobytes())
            (ROOT / 'firmware/main/reference_input.bin').write_bytes(tensor.tobytes())
            (ROOT / 'firmware/main/reference_output.bin').write_bytes(output.tobytes())
            shutil.copyfile(wav, ROOT / 'data/example_blackbird.wav')
    shutil.copyfile(destination, ROOT / 'firmware/main/model.tflite')
    (ROOT / 'firmware/main/feature_config.bin').write_bytes(convert_constants(handler.feature_constants))
    from biodcase_tiny.feature_extraction.nb_log32 import kLogLut
    constants = handler.feature_constants
    bank = constants.mel_constants
    arrays = {'kHanning': constants.hanning_window, 'kTwiddle': constants.fft_twiddle,
              'kFrequency': bank.ch_freq_starts, 'kWeightStart': bank.ch_weight_starts,
              'kWidth': bank.ch_widths, 'kWeights': bank.weights, 'kUnweights': bank.unweights,
              'kLogLut': kLogLut}
    header = '#pragma once\n#include <cstdint>\n'
    for name, values in arrays.items():
        dtype = 'uint16_t' if name == 'kLogLut' else 'int16_t'
        header += f'inline constexpr {dtype} {name}[] = {{' + ','.join(str(int(x)) for x in values) + '};\n'
    header += f'inline constexpr int kFftStart = {bank.fft_start_index}, kFftEnd = {bank.fft_end_index};\n'
    (ROOT / 'firmware/main/feature_constants.h').write_text(header)
    label_header = '#pragma once\ninline constexpr const char* kLabels[] = {' + ','.join(json.dumps(x) for x in labels) + '};\n'
    (ROOT / 'firmware/main/labels.h').write_text(label_header)
    report = {'model_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
              'model_bytes': destination.stat().st_size, 'input_shape': input_detail['shape'].tolist(),
              'input_quantization': input_detail['quantization'],
              'output_quantization': output_detail['quantization'],
              'correct': sum(row['actual'] == row['predicted'] for row in rows),
              'total': len(rows), 'examples': rows,
              'note': 'Small bundled sample set; this is not a validation-set accuracy estimate. No Brazilian species.'}
    (ROOT / 'results/tiny_host.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['model_bytes', 'input_shape', 'correct', 'total']}))


if __name__ == '__main__':
    main()
