"""Diagnostic source-object relink with object-qualified recovered text ordering.

No instruction or data bytes are read from the original binary or injected.
This does not establish the original compiler settings or dependency versions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def sections(path):
    rows = []
    pattern = re.compile(r'^\s*([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+(\d+)\s+(.+):\(([^)]+)\)$')
    for line in path.read_text().splitlines():
        m = pattern.match(line)
        if m:
            address, _, size, align, owner, section = m.groups()
            rows.append(dict(address=int(address, 16), size=int(size, 16), align=int(align),
                             owner=owner, section=section))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('mapping', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--constant-order', type=Path, help='Explicit recovered input-section permutations, without byte replacement')
    args = p.parse_args()
    def host(path):
        return Path(path)
    def vm(path):
        return str(path.resolve())
    manifest = json.loads((args.capture / 'link-input-manifest.json').read_text())
    rename = {}
    for r in manifest:
        assert hashlib.sha256(host(r['saved']).read_bytes()).hexdigest() == r['sha256'], r['saved']
        rename[r['original']] = r['saved']
    replay = json.loads((args.capture / 'relink-args.json').read_text())
    linker_args = replay['args'][:]
    script_index = linker_args.index('--script') + 1
    original_script = host(linker_args[script_index]).read_text()
    text = {r['address']: r for r in sections(args.capture / 'link.map')
            if r['size'] and r['section'].startswith('.text')}
    mapping = json.loads(args.mapping.read_text())
    assert mapping['direct_calls_enforced']
    lines, used, expanded = [], set(), []
    starts = sorted(r['candidate'] for r in mapping['rows'])
    bounds = dict(zip(starts, starts[1:] + [max(r['address'] + r['size'] for r in text.values())]))
    for r in mapping['rows']:
        children = [text[a] for a in sorted(text) if r['candidate'] <= a < bounds[r['candidate']]]
        assert children and children[0]['address'] == r['candidate']
        for row in children:
            owner = row['owner']
            if owner.endswith(')'):
                archive, member = owner.rsplit('(', 1)
                owner = rename[archive] + ':' + member[:-1]
            else:
                owner = rename[owner]
            key = (owner, row['section'])
            assert key not in used, key
            used.add(key)
            lines.append('    ' + json.dumps(owner) + '(' + json.dumps(row['section']) + ')')
            expanded.append(dict(expected=r['original'] + row['address'] - r['candidate'],
                                 baseline=row['address'], size=row['size'], owner=owner, section=row['section']))
    assert len(used) == len(text), (len(used), len(text))
    needle = '.text : { *(.text*) } :text'
    assert original_script.count(needle) == 1
    script = original_script.replace(needle, '.text : {\n' + '\n'.join(lines) + '\n    *(.text*)\n  } :text')
    if args.constant_order:
        permutations = json.loads(args.constant_order.read_text())
        baseline_sections = sections(args.capture / 'link.map')
        for group, moves in permutations.items():
            rows = [r for r in baseline_sections if r['section'].startswith(group)]
            by_address = {r['address']: r for r in rows if r['size']}
            replacement = {int(k): int(v) for k, v in moves.items()}
            assert set(replacement) == set(replacement.values()), 'Must be a permutation'
            ordered = [by_address[replacement[r['address']]] if r['size'] and r['address'] in replacement else r for r in rows]
            ordered_lines = []
            for row in ordered:
                owner = row['owner']
                if owner == '<internal>':
                    ordered_lines.append('    *(' + json.dumps(row['section']) + ')')
                    continue
                if owner.endswith(')'):
                    archive, member = owner.rsplit('(', 1)
                    owner = rename[archive] + ':' + member[:-1]
                else:
                    owner = rename[owner]
                ordered_lines.append('    ' + json.dumps(owner) + '(' + json.dumps(row['section']) + ')')
            needle = group + ' : { *(' + group + '*) } :rodata'
            assert script.count(needle) == 1
            script = script.replace(needle, group + ' : {\n' + '\n'.join(ordered_lines) + '\n    *(' + group + '*)\n  } :rodata')
    args.output.mkdir(exist_ok=False)
    if args.constant_order:
        (args.output / 'constant-order.json').write_text(args.constant_order.read_text())
    script_path = args.output / 'recovered-text-order.ld'
    script_path.write_text(script)
    (args.output / 'expanded-order.json').write_text(json.dumps(expanded, indent=2) + '\n')
    linker_args[script_index] = vm(script_path)
    linker_args[linker_args.index('-o') + 1] = vm(args.output / 'dao_v1.unstripped.so')
    linker_args.append('-Map=' + vm(args.output / 'link.map'))
    (args.output / 'relink-args.json').write_text(json.dumps(dict(linker=replay['linker'], args=linker_args), indent=2) + '\n')
    (args.output / 'provenance.json').write_text(json.dumps(dict(
        capture=str(args.capture), mapping=str(args.mapping),
        input_files_verified=len(manifest), ordered_sections=len(used), warning=__doc__), indent=2) + '\n')
    prefix = []
    with (args.output / 'link.log').open('w') as log:
        result = subprocess.run(prefix + [replay['linker']] + linker_args, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((args.output / 'link.log').read_text())
        raise SystemExit(result.returncode)
    subprocess.run(prefix + [replay['objcopy'], '--strip-all',
                             vm(args.output / 'dao_v1.unstripped.so'), vm(args.output / 'dao_v1.so')], check=True)
    binary = (args.output / 'dao_v1.so').read_bytes()
    print(json.dumps(dict(size=len(binary), sha256=hashlib.sha256(binary).hexdigest())))


if __name__ == '__main__':
    main()
