"""Compare the actual firmware C++ DSP with the official Python reference."""
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'upstream/BioDCASE-Tiny-2026'))
from feature_handler import FeatureHandler


def main():
    subprocess.run(['g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-Ifirmware/main', 'scripts/preprocess_host.cpp', 'firmware/main/preprocess.cpp',
                    '-o', 'results/preprocess_host.exe'], cwd=ROOT, check=True)
    handler = FeatureHandler(add_batch_dimension=True)
    cases = []
    for wav in sorted((ROOT / 'upstream/BioDCASE-Tiny-2026/submission/test_wav_files').rglob('*.wav')):
        audio, rate = sf.read(wav, dtype='int16')
        assert rate == 24000
        cases.append((wav.parent.name, audio))
    rng = np.random.default_rng(123)
    cases += [(f'random_amplitude_{amplitude}', rng.integers(-amplitude, amplitude + 1, 72000).astype(np.int16))
              for amplitude in (16, 1024, 32767)]
    cases += [('silence', np.zeros(72000, dtype=np.int16))]
    reports = []
    for name, pcm in cases:
        (ROOT / 'results/check_input.pcm').write_bytes(pcm.astype('<i2').tobytes())
        subprocess.run(['results/preprocess_host.exe', 'results/check_input.pcm', 'results/check_output.bin'], cwd=ROOT, check=True)
        actual = np.frombuffer((ROOT / 'results/check_output.bin').read_bytes(), dtype=np.int8)
        if name == 'silence':
            expected = np.full(5320, -128, dtype=np.int8)
        else:
            features = handler.extract(pcm)
            expected = np.clip(features / np.float32(0.003921568859368563) - 128, -128, 127).astype(np.int8).ravel()
        difference = actual.astype(int) - expected.astype(int)
        report = {'case': name, 'reference': 'defined_silence_behavior' if name == 'silence' else 'official_python',
                  'different': int(np.count_nonzero(difference)), 'max_error': int(np.abs(difference).max())}
        reports.append(report)
        print(report)
    (ROOT / 'results/preprocessing_parity.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
    if any(item['different'] for item in reports):
        raise SystemExit('C++ preprocessing differs from reference')
    print('PASS: 14 cases match the official Python reference exactly; silence fallback also passed')


if __name__ == '__main__':
    main()
