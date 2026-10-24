#!/usr/bin/env python3
"""Rebuild the user-specified AGI token and curve from their historical factory source set."""
from pathlib import Path
import hashlib
import subprocess
from rebuild import COMPILER_URL, COMPILER_SHA256, ROOT

compiler = ROOT / '.cache/solc/soljson-v0.8.26.js'
compiler.parent.mkdir(parents=True, exist_ok=True)
if not compiler.exists():
    subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', COMPILER_URL, '-o', str(compiler)], check=True)
if hashlib.sha256(compiler.read_bytes()).hexdigest() != COMPILER_SHA256:
    raise SystemExit('Pinned compiler SHA256 mismatch')
for name, contract in [('target-token', 'ClankLauncherToken'), ('target-curve', 'ClankBondingCurve')]:
    subprocess.run(['node', str(ROOT / 'scripts/compile_verified.cjs'),
                    str(ROOT / 'evidence/contracts/target-factory-sourcify.json'), str(compiler),
                    str(ROOT / f'.build/{name}.json'), f'contracts/{contract}.sol:{contract}'], check=True)
subprocess.run(['python3', str(ROOT / 'scripts/verify_target.py')], check=True)
