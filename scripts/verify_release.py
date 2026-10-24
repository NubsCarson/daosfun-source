"""Verify checked-in binaries, their ELF extent, and the recovered source manifest."""
import hashlib
import io
import json
from pathlib import Path
import sys
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = '5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d'


def main():
    original = (ROOT/'evidence/mainnet.so').read_bytes()
    rebuilt = (ROOT/'binaries/dao_v1.deployed.so').read_bytes()
    assert hashlib.sha256(original).hexdigest() == EXPECTED, 'Original hash mismatch'
    assert original == rebuilt, 'Rebuilt deployed bytes differ'
    with io.BytesIO(rebuilt) as f:
        elf = ELFFile(f)
        extent = elf['e_shoff'] + elf['e_shentsize'] * elf['e_shnum']
    assert extent == 1041728
    assert hashlib.sha256(rebuilt[:extent]).hexdigest() == '145716b96a30edc81413a77caea1c06c8aaf6adf3ad65b1576d6b9469f226e07'
    assert not any(rebuilt[extent:]), 'Allocation padding must be zero'
    manifest = json.loads((ROOT/'repro/source-manifest.json').read_text())
    for row in manifest['files']:
        path = ROOT/row['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], row['path']
    for row in json.loads((ROOT/'repro/evidence-manifest.json').read_text())['files']:
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
    print(json.dumps(dict(full_byte_identical=True, elf_byte_identical=True,
                         sha256=EXPECTED, size=len(original), zero_padding=len(original)-extent,
                         source_files_verified=len(manifest['files'])), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
