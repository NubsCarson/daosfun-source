"""Verify checked-in binaries, their ELF extent, and the recovered source manifest."""
import hashlib
import json
from pathlib import Path
import sys
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = '5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d'


def main():
    original = (ROOT/'evidence/mainnet.so').read_bytes()
    rebuilt = (ROOT/'binaries/dao_v1.deployed.so').read_bytes()
    elf_bytes = (ROOT/'binaries/dao_v1.so').read_bytes()
    assert hashlib.sha256(original).hexdigest() == EXPECTED, 'Original hash mismatch'
    assert original == rebuilt, 'Rebuilt deployed bytes differ'
    with (ROOT/'binaries/dao_v1.so').open('rb') as f:
        elf = ELFFile(f)
        extent = elf['e_shoff'] + elf['e_shentsize'] * elf['e_shnum']
    assert len(elf_bytes) == extent == 1041728
    assert original[:extent] == elf_bytes and not any(original[extent:])
    manifest = json.loads((ROOT/'repro/source-manifest.json').read_text())
    for row in manifest['files']:
        path = ROOT/row['path']
        # Registry location is the only packaging change to the frozen workspace.
        if row['path'] == '.cargo/config.toml':
            continue
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'], row['path']
    for row in json.loads((ROOT/'repro/evidence-manifest.json').read_text())['files']:
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
    print(json.dumps(dict(full_byte_identical=True, elf_byte_identical=True,
                         sha256=EXPECTED, size=len(original), zero_padding=len(original)-extent,
                         source_files_verified=len(manifest['files'])-1), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
