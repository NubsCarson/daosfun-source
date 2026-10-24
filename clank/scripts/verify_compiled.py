#!/usr/bin/env python3
"""Prove local compilation matches a captured runtime, permitting declared immutables only."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unhex(value):
    return bytes.fromhex(value.removeprefix('0x'))


def verify(record_path, compiled_path, runtime_path, rebuilt_path, report_path):
    record = json.loads(record_path.read_text())
    compiled = json.loads(compiled_path.read_text())
    captured = runtime_path.read_bytes()
    published = record['runtimeBytecode']
    artifact = compiled['artifact']['evm']['deployedBytecode']
    raw = unhex(artifact['object'])
    if artifact.get('linkReferences'):
        raise ValueError('Linked-library verification is not implemented; refusing to normalize it')
    if raw != unhex(published['recompiledBytecode']):
        raise ValueError('Local raw runtime differs from Sourcify recompiled runtime')
    if captured != unhex(published['onchainBytecode']):
        raise ValueError('Captured RPC runtime differs from Sourcify on-chain runtime')
    if compiled['contract'] != record['compilation']['fullyQualifiedName']:
        raise ValueError('Compiler artifact has a different contract identity')
    if compiled['compilerVersion'].split('.Emscripten')[0] != record['compilation']['compilerVersion']:
        raise ValueError('Compiler version differs from the verification record')
    refs = artifact.get('immutableReferences', {})
    declared = published.get('immutableReferences', {})
    if refs != declared:
        raise ValueError('Local compiler immutable offsets differ from Sourcify offsets')
    values = (published.get('transformationValues') or {}).get('immutables', {})
    if set(refs) != set(values):
        raise ValueError('Missing or extra deployment immutable values')
    rebuilt = bytearray(raw)
    patches = []
    used = set()
    for identity, ranges in refs.items():
        value = unhex(values[identity])
        for entry in ranges:
            offset, length = entry['start'], entry['length']
            if length != len(value) or offset < 0 or offset + length > len(raw):
                raise ValueError('Invalid immutable length or range')
            span = set(range(offset, offset + length))
            if used & span:
                raise ValueError('Overlapping immutable ranges')
            used.update(span)
            if raw[offset:offset + length] != bytes(length):
                raise ValueError('Compiler immutable placeholder is not zero-filled')
            rebuilt[offset:offset + length] = value
            patches.append({'id': identity, 'start': offset, 'length': length, 'value': values[identity]})
    if bytes(rebuilt) != captured:
        raise ValueError('Locally compiled runtime with deployment immutables is not byte identical')
    rebuilt_path.parent.mkdir(parents=True, exist_ok=True)
    rebuilt_path.write_bytes(rebuilt)
    report = {
        'contract': compiled['contract'], 'address': record['address'], 'chainId': record['chainId'],
        'compilerVersion': compiled['compilerVersion'], 'compilerSha256': compiled['compilerSha256'],
        'inputSha256': compiled['inputSha256'], 'runtimeBytes': len(captured),
        'capturedSha256': sha(captured), 'rebuiltSha256': sha(rebuilt), 'rawCompilerSha256': sha(raw),
        'byteIdentical': True, 'rawCompilerEqualsSourcify': True,
        'rpcEqualsSourcify': True, 'immutablePatches': patches,
        'scope': 'Runtime bytes only; deployment-specific immutables supplied by the published verification record and checked against RPC bytes. No other substitutions, metadata removal, or ignored ranges.',
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{record["address"]}: {len(captured):,} runtime bytes identical; SHA256 {sha(rebuilt)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('compiled', type=Path)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('rebuilt', type=Path)
    parser.add_argument('report', type=Path)
    a = parser.parse_args()
    verify(a.record, a.compiled, a.runtime, a.rebuilt, a.report)
