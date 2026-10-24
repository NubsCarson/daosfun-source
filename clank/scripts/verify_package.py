#!/usr/bin/env python3
"""Offline integrity and complete-byte comparison of the packaged Clank recovery."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def digest(data): return hashlib.sha256(data).hexdigest()
def main():
    manifest=json.loads((ROOT/'evidence/package-manifest.json').read_text())
    for name,expected in manifest['files'].items():
        path=ROOT/name
        if digest(path.read_bytes()) != expected: raise ValueError(f'File hash mismatch: {name}')
    reports=list((ROOT/'evidence/build').glob('*.json'))
    if len(reports)!=17: raise ValueError('Expected exactly 17 runtime verification reports')
    for path in reports:
        d=json.loads(path.read_text());name=path.stem
        captured=(ROOT/f'evidence/contracts/{name}.runtime.bin').read_bytes()
        rebuilt=(ROOT/f'binaries/{name}.runtime.bin').read_bytes()
        if captured != rebuilt: raise ValueError(f'Complete runtime mismatch: {name}')
        if len(rebuilt)!=d['runtimeBytes'] or digest(rebuilt)!=d['rebuiltSha256'] or digest(captured)!=d['capturedSha256']:
            raise ValueError(f'Runtime report mismatch: {name}')
    for kind in ('creation','runtime'):
        if (ROOT/f'evidence/contracts/target-token.user-{kind}.bin').read_bytes() != (ROOT/f'binaries/target-token.{kind}.bin').read_bytes():
            raise ValueError(f'User-supplied target {kind} differs from rebuilt artifact')
    print(json.dumps({'filesVerified':len(manifest['files']),'runtimePairsByteIdentical':len(reports),'targetCreationAndRuntimeByteIdentical':True},indent=2))
if __name__=='__main__':main()
