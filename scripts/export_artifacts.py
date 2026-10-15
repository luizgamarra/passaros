"""Make the compiled firmware portable without the build directory."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'


def main():
    global ARTIFACTS
    if len(sys.argv) > 1:
        ARTIFACTS = Path(sys.argv[1]).resolve()
    args_path = ARTIFACTS / 'flasher_args.json'
    args = json.loads(args_path.read_text())
    args['flash_files'] = {address: Path(name).name for address, name in args['flash_files'].items()}
    for key in ('bootloader', 'app', 'partition-table'):
        args[key]['file'] = Path(args[key]['file']).name
    args_path.write_text(json.dumps(args, indent=2), encoding='utf-8')
    tokens = [token.replace('_', '-') if token.startswith('--') else token for token in args['write_flash_args']]
    for address, name in sorted(args['flash_files'].items(), key=lambda item: int(item[0], 16)):
        tokens.extend([address, name])
    (ARTIFACTS / 'flash_args').write_text('\n'.join(tokens) + '\n', encoding='utf-8')
    # Merging is offline and opens no serial device.
    subprocess.run([sys.executable, '-m', 'esptool', '--chip', 'esp32s3', 'merge-bin',
                    '--output', 'flash-full.bin', *tokens], cwd=ARTIFACTS, check=True)


if __name__ == '__main__':
    main()
