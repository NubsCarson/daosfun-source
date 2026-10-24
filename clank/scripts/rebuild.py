#!/usr/bin/env python3
"""Download the pinned official compiler, rebuild selected records, and compare runtime bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPILER_URL = 'https://binaries.soliditylang.org/wasm/soljson-v0.8.26+commit.8a97fa7a.js'
COMPILER_SHA256 = 'db85e5396f523cc1a53c4c4d742e204f6dcba1a05842623d73be946809e11cd6'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='*', default=['factory'], help='Record names, such as factory or eth-router')
    args = parser.parse_args()
    compiler = ROOT / '.cache/solc/soljson-v0.8.26.js'
    compiler.parent.mkdir(parents=True, exist_ok=True)
    if not compiler.exists():
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                        COMPILER_URL, '-o', str(compiler)], check=True)
    if hashlib.sha256(compiler.read_bytes()).hexdigest() != COMPILER_SHA256:
        raise SystemExit('Pinned compiler SHA256 mismatch; remove the invalid cached compiler and retry')
    for name in args.names:
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in name):
            raise SystemExit('Record names may only contain lowercase letters, digits, hyphens, and underscores')
        record = ROOT / f'evidence/contracts/{name}-sourcify.json'
        data = json.loads(record.read_text())
        if data['compilation']['compilerVersion'] != '0.8.26+commit.8a97fa7a':
            raise SystemExit(f'{name}: unsupported compiler; do not substitute a different compiler version')
        output = ROOT / f'.build/{name}.json'
        subprocess.run(['node', str(ROOT / 'scripts/compile_verified.cjs'), str(record),
                        str(compiler), str(output)], check=True)
        subprocess.run(['python3', str(ROOT / 'scripts/verify_compiled.py'), str(record), str(output),
                        str(ROOT / f'evidence/contracts/{name}.runtime.bin'),
                        str(ROOT / f'binaries/{name}.runtime.bin'),
                        str(ROOT / f'evidence/build/{name}.json')], check=True)


if __name__ == '__main__':
    main()
