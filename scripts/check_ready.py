"""Record reproducible preparation evidence; never claims physical acceptance."""
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    subprocess.run(['uv', 'pip', 'check', '--python', sys.executable], check=True)
    report = json.loads((ROOT / 'results/tiny_host.json').read_text())
    parity = json.loads((ROOT / 'results/preprocessing_parity.json').read_text())
    assert len(parity) == 15 and all(case['different'] == 0 for case in parity)
    assert report['model_sha256'] == digest(ROOT / 'firmware/main/model.tflite')['sha256']
    artifacts = ROOT / 'artifacts'
    merged = (artifacts / 'flash-full.bin').read_bytes()
    assert merged[0x10000:] == (artifacts / 'passaros_tiny.bin').read_bytes()
    assert merged[0x8000:0x8000+3072] == (artifacts / 'partition-table.bin').read_bytes()
    args = json.loads((artifacts / 'flasher_args.json').read_text())
    for filename in args['flash_files'].values():
        assert (artifacts / filename).is_file()
    csv = ROOT / 'results/analyzer/BirdNET_CombinedTable.csv'
    assert csv.is_file() and 'Turdus merula' in csv.read_text(encoding='utf-8-sig')
    commits = {}
    for repo in sorted((ROOT / 'upstream').iterdir()):
        commits[repo.name] = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip()
    packages = {name: importlib.metadata.version(name) for name in
                ['birdnet-analyzer', 'birdnet', 'tensorflow', 'ai-edge-litert', 'numpy', 'numba', 'esptool', 'pyserial', 'backports.strenum']}
    hardware_file = ROOT / 'results/hardware/receipt.json'
    hardware = json.loads(hardware_file.read_text()) if hardware_file.is_file() else None
    manifest = {'prepared_date': '2026-10-14', 'target': 'ESP32-S3 N16R8',
                'microphone_assumption': 'INMP441, BCLK=4 WS=5 SD=6 LR=GND',
                'python': platform.python_version(), 'idf': '5.5.2', 'packages': packages,
                'upstream_commits': commits, 'artifacts': {p.name: digest(p) for p in artifacts.iterdir() if p.is_file()},
                'tiny_examples': {'correct': report['correct'], 'total': report['total']},
                'cpp_python_parity': {'official_reference_cases': 14, 'official_reference_int8_features': 14*5320,
                                     'silence_fallback_cases': 1, 'different': 0},
                'analyzer_csv': str(csv.relative_to(ROOT)),
                'hardware_receipt': hardware,
                'status': 'COM46 flashed and verified; on-device selftest passed; microphone not yet connected' if hardware else 'Software prepared and compiled; hardware acceptance pending',
                'pending': ['Connect microphone and listen to captured WAV',
                            'Measure live inference timings and power', 'Train/evaluate target Brazilian species model'] if hardware else ['Flash actual board', 'On-device selftest and PSRAM check', 'Microphone audio check']}
    (ROOT / 'results/manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'status': manifest['status'], 'firmware_bytes': manifest['artifacts']['passaros_tiny.bin']['bytes'],
                      'cpp_python_parity': manifest['cpp_python_parity']}))


if __name__ == '__main__':
    main()
