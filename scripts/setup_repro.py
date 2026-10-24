#!/usr/bin/env python3
"""Fetch the pinned compiler and Cargo.lock crates, checking recorded hashes.

Requires Python 3.11+. Sources: official Anza release and static.crates.io.
No build scripts are executed during setup.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import time
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://github.com/anza-xyz/platform-tools/releases/download/v1.41/platform-tools-linux-x86_64.tar.bz2'


def download(url, path):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'daosfun-source-reproduction'}), timeout=120) as response, path.open('wb') as output:
                shutil.copyfileobj(response, output)
            return
        except Exception:
            if attempt==2:
                raise
            time.sleep(2**attempt)


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def verify_toolchain(path):
    for row in json.loads((ROOT/'repro/toolchain-components.json').read_text())['components']:
        actual=sha(path/row['path'])
        if actual!=row['sha256']:
            raise RuntimeError('Toolchain checksum mismatch: '+row['path'])


def setup_toolchain(destination):
    if destination.exists():
        verify_toolchain(destination)
        return
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp:
        tmp=Path(tmp)
        archive=tmp/'platform-tools.tar.bz2'
        download(URL,archive)
        extracted=tmp/'extracted';extracted.mkdir()
        with tarfile.open(archive,'r:bz2') as tar:
            # Python's data filter rejects paths/link targets outside extracted.
            tar.extractall(extracted,filter='data')
        candidates=[extracted]+[x for x in extracted.iterdir() if x.is_dir()]
        root=next((x for x in candidates if (x/'rust/bin/rustc').exists()),None)
        if root is None:
            raise RuntimeError('Unexpected platform-tools archive layout')
        verify_toolchain(root)
        root.rename(destination)


def setup_vendor(destination):
    packages=[p for p in tomllib.loads((ROOT/'Cargo.lock').read_text())['package'] if p.get('source','').startswith('registry+')]
    destination.mkdir(parents=True,exist_ok=True)
    def install(package):
        name,version=package['name'],package['version']
        target=destination/(name+'-'+version)
        if target.exists():
            manifest=json.loads((target/'.cargo-checksum.json').read_text())
            if manifest['package']!=package['checksum']:
                raise RuntimeError('Existing vendor package hash mismatch: '+str(target))
            for file,digest in manifest['files'].items():
                if sha(target/file)!=digest:
                    raise RuntimeError('Existing vendor file hash mismatch: '+str(target/file))
            return name,version
        with tempfile.TemporaryDirectory(dir=destination) as temp:
            temp=Path(temp); archive=temp/'crate.tar.gz'; content=temp/'content';content.mkdir()
            download(f'https://static.crates.io/crates/{name}/{name}-{version}.crate',archive)
            if sha(archive)!=package['checksum']:
                raise RuntimeError('Cargo.lock checksum mismatch: '+name+' '+version)
            prefix=name+'-'+version
            with tarfile.open(archive,'r:gz') as tar:
                for member in tar.getmembers():
                    parts=PurePosixPath(member.name).parts
                    if not parts or parts[0]!=prefix or '..' in parts or member.issym() or member.islnk():
                        raise RuntimeError('Unexpected crate archive path: '+member.name)
                tar.extractall(content,filter='data')
            crate=content/prefix
            files={str(f.relative_to(crate)):sha(f) for f in sorted(crate.rglob('*')) if f.is_file() and f.name!='.cargo-checksum.json'}
            (crate/'.cargo-checksum.json').write_text(json.dumps({'files':files,'package':package['checksum']},sort_keys=True))
            crate.rename(target)
        return name,version
    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(install,packages):
            pass
    print('Verified',len(packages),'registry packages')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--toolchain',type=Path,default=ROOT/'.cache/platform-tools-v1.41')
    p.add_argument('--vendor',type=Path,default=ROOT/'vendor')
    p.add_argument('--vendor-only',action='store_true')
    p.add_argument('--toolchain-only',action='store_true')
    args=p.parse_args()
    if args.vendor_only and args.toolchain_only:
        p.error('Choose at most one mode')
    if not args.vendor_only:
        setup_toolchain(args.toolchain.resolve());print('Verified platform-tools v1.41')
    if not args.toolchain_only:
        setup_vendor(args.vendor.resolve())


if __name__=='__main__':
    main()
