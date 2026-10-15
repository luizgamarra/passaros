"""Record verified flash/boot evidence without changing the board."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_log(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig', errors='replace')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    release = ROOT / 'releases/20261014-COM46-validado'
    log = read_log(ROOT / 'results/hardware/serial-final.log')
    verify = read_log(ROOT / 'results/hardware/verify-final.log')
    assert 'SELFTEST_FEATURES: divergencias=0/5320' in log and 'SELFTEST_OK' in log
    assert 'erro_max_LSB=1 previsto=Eurasian Blackbird esperado=Eurasian Blackbird' in log
    assert 'Verification successful' in verify
    backup = ROOT / 'backups/COM46-20261014-antes.bin'
    assert backup.stat().st_size == 16777216
    receipt = {'date': '2026-10-14', 'port': 'COM46', 'chip': 'ESP32-S3 v0.2',
               'mac': '98:3d:ae:e0:fa:f0', 'flash_bytes': 16777216, 'psram_bytes': 8388608,
               'psram_test': 'OK', 'firmware_path': str(release / 'flash-full.bin'),
               'application_path': str(release / 'passaros_tiny.bin'),
               'firmware_bytes': (release / 'flash-full.bin').stat().st_size,
               'application_bytes': (release / 'passaros_tiny.bin').stat().st_size,
               'firmware_sha256': digest(release / 'flash-full.bin'),
               'application_sha256': digest(release / 'passaros_tiny.bin'),
               'backup_path': str(backup), 'backup_sha256': digest(backup), 'flash_verified': True,
               'features_different': 0, 'features_total': 5320, 'output_max_error_lsb': 1,
               'predicted': 'Eurasian Blackbird', 'expected': 'Eurasian Blackbird',
               'arena_used_bytes': 202444, 'microphone_rms': 0.0,
               'microphone_status': 'Not connected, confirmed by user; audio test pending',
               'sd_card_required': False,
               'kernel_fix': 'TFLM reference fully connected handles per-channel quantization; ESP-NN convolutions retained'}
    for path in (ROOT / 'results/hardware/receipt.json', release / 'receipt.json'):
        path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    hashes = {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
              for path in release.iterdir() if path.is_file() and path.name != 'hashes.json'}
    (release / 'hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print(json.dumps({key: receipt[key] for key in ['firmware_path', 'firmware_sha256', 'features_different', 'output_max_error_lsb']}))


if __name__ == '__main__':
    main()
