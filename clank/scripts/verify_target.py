#!/usr/bin/env python3
"""Verify AGI's locally compiled historical token/curve artifacts against saved evidence."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    state = json.loads((ROOT / 'evidence/contracts/target-state.json').read_text())
    calls = {(x['address'].lower(), x['function']): x.get('result') for x in state['calls']}
    reports = []
    for name, address in [('target-token', state['token']), ('target-curve', state['curve'])]:
        compiled = json.loads((ROOT / f'.build/{name}.json').read_text())
        artifact = compiled['artifact']['evm']
        runtime = artifact['deployedBytecode']
        if runtime.get('linkReferences'):
            raise ValueError('Linked library references are not supported')
        raw = bytes.fromhex(runtime['object'])
        live = (ROOT / f'evidence/contracts/{name}.runtime.bin').read_bytes()
        if len(raw) != len(live):
            raise ValueError('Runtime length mismatch')
        refs = runtime.get('immutableReferences', {})
        names = compiled['immutableNames']
        expected_values = {}
        creation_proof = None
        if name == 'target-token':
            original = (ROOT / 'evidence/contracts/target-token.user-creation.bin').read_bytes()
            creation = bytes.fromhex(artifact['bytecode']['object'])
            if not original.startswith(creation):
                raise ValueError('Original creation payload does not begin with local compiled initcode')
            args = original[len(creation):]
            if len(args) < 7 * 32:
                raise ValueError('Constructor tuple is truncated')
            # Constructor: name, symbol, metadata, deployer, curve, factory, supply.
            expected_values = {key: args[index * 32:(index + 1) * 32]
                               for key, index in [('deployer', 3), ('curve', 4), ('launchFactory', 5)]}
            if set(names[x] for x in refs) != set(expected_values):
                raise ValueError('Unexpected token immutable declarations')
            for key, value in expected_values.items():
                if value[:12] != bytes(12):
                    raise ValueError('Noncanonical constructor address')
                if calls.get((address.lower(), key + '()')) != '0x' + value.hex():
                    raise ValueError('Constructor address differs from captured getter')
            rebuilt_creation = creation + args
            if rebuilt_creation != original:
                raise ValueError('Rebuilt complete creation payload differs')
            (ROOT / 'binaries/target-token.creation.bin').write_bytes(rebuilt_creation)
            provided_runtime = (ROOT / 'evidence/contracts/target-token.user-runtime.bin').read_bytes()
            if provided_runtime != live:
                raise ValueError('User runtime differs from captured RPC runtime')
            creation_proof = {'compiledInitcodeBytes': len(creation), 'constructorArgumentsBytes': len(args),
                              'completeCreationBytes': len(original), 'completeCreationSha256': sha(original),
                              'compiledInitcodeSha256': sha(creation), 'constructorArgumentsSha256': sha(args),
                              'byteIdentical': True,
                              'scope': 'Locally compiled initcode plus the original ABI constructor argument suffix; token immutable addresses are decoded from this suffix and checked against captured getters.'}
        rebuilt = bytearray(raw)
        used = set()
        patches = []
        for identity, ranges in refs.items():
            variable = names[identity]
            values = {live[r['start']:r['start'] + r['length']] for r in ranges}
            if len(values) != 1:
                raise ValueError('Inconsistent immutable value across reference sites')
            value = expected_values.get(variable, next(iter(values)))
            captured_getter = calls.get((address.lower(), variable + '()'))
            if captured_getter is not None and captured_getter != '0x' + value.hex():
                raise ValueError('Immutable does not equal captured getter')
            for r in ranges:
                start, length = r['start'], r['length']
                if start < 0 or start + length > len(raw) or len(value) != length:
                    raise ValueError('Invalid immutable range')
                span = set(range(start, start + length))
                if used & span or raw[start:start + length] != bytes(length):
                    raise ValueError('Invalid or overlapping compiler placeholder')
                used.update(span)
                rebuilt[start:start + length] = value
                patches.append({'id': identity, 'variable': variable, 'start': start, 'length': length,
                                'value': '0x' + value.hex(),
                                'origin': 'constructor argument' if name == 'target-token' else 'captured runtime',
                                'capturedGetterMatches': captured_getter is not None})
        if bytes(rebuilt) != live:
            raise ValueError('Complete runtime differs outside compiler-declared immutable sites')
        (ROOT / f'binaries/{name}.runtime.bin').write_bytes(rebuilt)
        report = {'contract': compiled['contract'], 'address': address, 'chainId': state['chainId'],
                  'block': state['block'], 'compilerVersion': compiled['compilerVersion'],
                  'compilerSha256': compiled['compilerSha256'], 'inputSha256': compiled['inputSha256'],
                  'runtimeBytes': len(live), 'capturedSha256': sha(live), 'rebuiltSha256': sha(rebuilt),
                  'rawCompilerSha256': sha(raw), 'byteIdentical': True, 'immutablePatches': patches,
                  'creation': creation_proof,
                  'scope': 'Complete runtime equality including metadata. Only compiler-declared immutable sites populated. Curve values are extracted from capture; available public getters corroborate those values. No constructor execution is claimed by this script.'}
        (ROOT / f'evidence/build/{name}.json').write_text(json.dumps(report, indent=2) + '\n')
        reports.append(report)
        print(f'{name}: {len(live):,} runtime bytes identical, SHA256 {sha(live)}')
    return reports


if __name__ == '__main__':
    (ROOT / 'binaries').mkdir(exist_ok=True)
    (ROOT / 'evidence/build').mkdir(parents=True, exist_ok=True)
    verify()
