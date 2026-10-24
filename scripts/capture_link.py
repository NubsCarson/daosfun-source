#!/usr/bin/env python3
"""Capture genuine compiler-produced link inputs for repeatable layout diagnostics."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

linker = os.environ['RECOVERY_REAL_LINKER']
args = sys.argv[1:]
output = args[args.index('-o') + 1] if '-o' in args else ''
if Path(output).name not in ('dao_v1.so', 'libdao_v1.so'):
    raise SystemExit(subprocess.call([linker] + args))
root = Path(os.environ['RECOVERY_CAPTURE_DIR'])
inputs = root / 'link-inputs'
inputs.mkdir(exist_ok=False)
records = []
replay = []
for i, arg in enumerate(args):
    if i and args[i - 1] == '-o':
        replay.append(str(root / 'relinked.so'))
        continue
    prefix = ''
    candidate = arg
    if arg.startswith('--version-script='):
        prefix, candidate = '--version-script=', arg.split('=', 1)[1]
    path = Path(candidate)
    if path.is_file():
        dest = inputs / (str(i) + '-' + path.name)
        shutil.copy2(path, dest)
        records.append(dict(argument=i, original=str(path), saved=str(dest),
                            sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
        replay.append(prefix + str(dest))
    else:
        replay.append(arg)
(root / 'link-input-manifest.json').write_text(json.dumps(records, indent=2) + '\n')
(root / 'relink-args.json').write_text(json.dumps(dict(linker=linker, objcopy=os.environ['RECOVERY_OBJCOPY'], args=replay), indent=2) + '\n')
(root / 'original-link-args.json').write_text(json.dumps(args, indent=2) + '\n')
raise SystemExit(subprocess.call([linker] + args + ['-Map=' + str(root / 'link.map')]))
