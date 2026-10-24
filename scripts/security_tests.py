"""Run local security reproductions; never accesses RPC or submits transactions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.build/security')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    tests = [ROOT / 'audit/poc_finalize_cross_pool.py', *sorted((ROOT / 'audit/pocs').glob('poc_*.py'))]
    results = []
    for test in tests:
        result = subprocess.run([sys.executable, str(test)], cwd=ROOT, capture_output=True, text=True)
        (args.output / (test.stem + '.log')).write_text(result.stdout + result.stderr)
        passed = result.returncode == 0
        if test.name == 'poc_finalize_cross_pool.py':
            passed &= 'Y wallet after 1100' in result.stdout and "{'Custom': 6040}" in result.stdout
        results.append(dict(test=str(test.relative_to(ROOT)), passed=passed, exit_code=result.returncode))
        print(test.name, 'PASS' if passed else 'FAIL', flush=True)
    summary = dict(original_sha256=hashlib.sha256((ROOT/'evidence/mainnet.so').read_bytes()).hexdigest(), results=results, passed=all(x['passed'] for x in results))
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
