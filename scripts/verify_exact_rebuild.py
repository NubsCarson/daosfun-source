"""Compare a source-built ELF and optional zero allocation padding byte-for-byte."""
import argparse
import hashlib
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original', type=Path)
    p.add_argument('rebuilt', type=Path)
    p.add_argument('report', type=Path)
    p.add_argument('--padded-output', type=Path)
    args = p.parse_args()
    original, rebuilt = args.original.read_bytes(), args.rebuilt.read_bytes()
    with args.original.open('rb') as f:
        elf = ELFFile(f)
        extent = max(elf['e_shoff'] + elf['e_shentsize'] * elf['e_shnum'],
                     *(s['sh_offset'] + s['sh_size'] for s in elf.iter_sections() if s['sh_type'] != 'SHT_NOBITS'))
        sections = [{ 'name': s.name, 'offset': s['sh_offset'], 'size': s['sh_size'],
                      'identical': original[s['sh_offset']:s['sh_offset']+s['sh_size']] == rebuilt[s['sh_offset']:s['sh_offset']+s['sh_size']] }
                    for s in elf.iter_sections() if s['sh_type'] != 'SHT_NOBITS']
    differences = [i for i, (a, b) in enumerate(zip(original[:extent], rebuilt)) if a != b]
    exact_elf = len(rebuilt) == extent and rebuilt == original[:extent]
    padding = original[extent:]
    report = dict(original=str(args.original.resolve()), rebuilt=str(args.rebuilt.resolve()),
                  original_sha256=hashlib.sha256(original).hexdigest(), rebuilt_sha256=hashlib.sha256(rebuilt).hexdigest(),
                  original_size=len(original), rebuilt_size=len(rebuilt), elf_extent=extent,
                  differing_elf_bytes=len(differences), first_differences=differences[:30],
                  exact_elf=exact_elf, allocation_padding_bytes=len(padding),
                  allocation_padding_all_zero=not any(padding), sections=sections)
    if args.padded_output:
        assert exact_elf and not any(padding), 'Refuse to pad a mismatching ELF or copy nonzero original data'
        assert not args.padded_output.exists(), 'Do not overwrite prior output'
        # Generate fresh zero bytes; never copy original executable contents.
        padded = rebuilt + bytes(len(padding))
        args.padded_output.write_bytes(padded)
        report.update(padded_output=str(args.padded_output.resolve()),
                      padded_sha256=hashlib.sha256(padded).hexdigest(), full_byte_identical=padded == original)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if exact_elf else 1


if __name__ == '__main__':
    raise SystemExit(main())
