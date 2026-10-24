#!/usr/bin/env python3
"""Build genuine Rust objects, apply recovered section ordering, verify exact bytes.

Run on Linux with official x86_64 platform-tools v1.41. No original executable
bytes are supplied to compilation/linking. The original is a verifier input only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_SHA = '5020271255ea678fc110fed4671a86b1b7268acad04f990c590decd92091143d'
ELF_SHA = '145716b96a30edc81413a77caea1c06c8aaf6adf3ad65b1576d6b9469f226e07'
ELF_SIZE = 1041728
DEPLOYED_SIZE = 1120784


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--toolchain', type=Path, default=os.environ.get('TOOLCHAIN', ROOT / '.cache/platform-tools-v1.41'))
    p.add_argument('--vendor', type=Path, default=os.environ.get('VENDOR', ROOT / 'vendor'))
    p.add_argument('--output', type=Path, default=ROOT / '.build/exact')
    p.add_argument('--target', type=Path, default=os.environ.get('TARGET'))
    p.add_argument('--jobs', type=int, default=4)
    args = p.parse_args()
    toolchain, vendor, output = args.toolchain.resolve(), args.vendor.resolve(), args.output.resolve()
    target = args.target.resolve() if args.target else output / 'target'
    if output.exists() or target.exists():
        p.error('Output and target cache must not exist: use fresh paths for independent evidence')
    if not vendor.is_dir():
        p.error('Vendor directory missing; see docs/BUILD.md')
    original = ROOT / 'evidence/mainnet.so'
    if digest(original) != ORIGINAL_SHA:
        p.error('Original binary differs from the published capture')
    fingerprints = json.loads((ROOT / 'repro/toolchain-components.json').read_text())
    verified = []
    for item in fingerprints['components']:
        actual = digest(toolchain / item['path'])
        if actual != item['sha256']:
            p.error('Toolchain fingerprint mismatch: ' + item['path'])
        verified.append({'path': item['path'], 'sha256': actual})
    output.mkdir(parents=True)
    capture = output / 'capture'
    capture.mkdir()
    source_files = [ROOT / 'Cargo.toml', ROOT / 'Cargo.lock', ROOT / 'Anchor.toml']
    source_files += sorted(f for f in (ROOT / 'programs').rglob('*') if f.is_file())
    source_files += sorted(f for f in (ROOT / '.cargo').rglob('*') if f.is_file())
    source_manifest = [{'path':str(f.relative_to(ROOT)), 'sha256':digest(f)} for f in source_files]
    (output / 'source-manifest.json').write_text(json.dumps(source_manifest, indent=2)+'\n')
    (output / 'toolchain-verification.json').write_text(json.dumps(verified, indent=2)+'\n')
    env = os.environ.copy()
    for key in ('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER'):
        env.pop(key, None)
    env.update({
        'RUSTC':str(toolchain/'rust/bin/rustc'),
        'RUSTDOC':str(toolchain/'rust/bin/rustdoc'),
        'PATH':str(toolchain/'rust/bin')+os.pathsep+str(toolchain/'llvm/bin')+os.pathsep+env['PATH'],
        'CC':str(toolchain/'llvm/bin/clang'), 'AR':str(toolchain/'llvm/bin/llvm-ar'),
        'CARGO_INCREMENTAL':'0', 'CARGO_TARGET_DIR':str(target),
        'CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS':'-Zremap-cwd-prefix=',
        'CARGO_TARGET_SBF_SOLANA_SOLANA_LINKER':str(ROOT/'scripts/capture_link.py'),
        'RECOVERY_REAL_LINKER':str(toolchain/'rust/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld'),
        'RECOVERY_OBJCOPY':str(toolchain/'llvm/bin/llvm-objcopy'),
        'RECOVERY_CAPTURE_DIR':str(capture),
        'CARGO_BUILD_JOBS':str(args.jobs),
    })
    command = [str(toolchain/'rust/bin/cargo'), 'build', '--release', '--target', 'sbf-solana-solana',
               '--locked', '--offline', '--config', 'source.vendored-sources.directory='+json.dumps(str(vendor))]
    (output/'command.json').write_text(json.dumps({'command':command, 'target_initially_absent':True,
        'rustflags':env['CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS']}, indent=2)+'\n')
    with (output/'build.log').open('w') as log:
        subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    log_text=(output/'build.log').read_text()
    if 'Stack offset ' in log_text and 'exceeded' in log_text or 'overwrites values in the frame' in log_text:
        raise RuntimeError('SBF stack diagnostic; inspect build.log')
    linked = output / 'linked'
    subprocess.run([sys.executable,str(ROOT/'scripts/relink.py'),str(capture),
                   str(ROOT/'repro/order-mapping.json'),str(linked),
                   '--constant-order',str(ROOT/'repro/constant-order.json')],env=env,check=True)
    elf=(linked/'dao_v1.so').read_bytes()
    captured=original.read_bytes()
    if len(elf)!=ELF_SIZE or elf!=captured[:ELF_SIZE] or hashlib.sha256(elf).hexdigest()!=ELF_SHA:
        raise RuntimeError('Rebuilt ELF differs from the reference; candidate preserved for analysis')
    if len(captured)!=DEPLOYED_SIZE or any(captured[ELF_SIZE:]):
        raise RuntimeError('Unexpected account allocation padding')
    deployed=elf+bytes(DEPLOYED_SIZE-ELF_SIZE)
    (linked/'dao_v1.deployed.so').write_bytes(deployed)
    assert deployed==captured
    proof={'elf_byte_identical':True,'full_byte_identical':True,'elf_size':ELF_SIZE,
           'full_size':DEPLOYED_SIZE,'zero_padding_size':DEPLOYED_SIZE-ELF_SIZE,
           'elf_sha256':hashlib.sha256(elf).hexdigest(),'full_sha256':hashlib.sha256(deployed).hexdigest(),
           'target_initially_absent':True,'toolchain_files_verified':len(verified)}
    (output/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))


if __name__=='__main__':
    main()
