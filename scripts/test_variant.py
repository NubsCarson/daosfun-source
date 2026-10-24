"""Run existing differential suites against another build, preserving baseline evidence."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def rejected_as_duplicate(value):
    if isinstance(value, dict):
        return any(rejected_as_duplicate(v) for v in value.values())
    if isinstance(value, list):
        return any(rejected_as_duplicate(v) for v in value)
    return value == 'AlreadyProcessed'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('binary', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    binary, destination = args.binary.resolve(), args.output.resolve()
    if destination.exists():
        raise SystemExit('Use a new output directory so earlier evidence is preserved.')
    destination.mkdir(parents=True)
    (destination / 'scripts').mkdir()
    (destination / 'evidence').mkdir()
    for path in (ROOT / 'scripts').glob('*.py'):
        shutil.copy2(path, destination / 'scripts' / path.name)
    # Fixtures are linked individually. Test result files are never linked.
    for path in (ROOT / 'evidence').iterdir():
        if (path.is_file() and not path.name.startswith('differential')
                and not path.name.endswith(('-probe.json', '-probes.json'))):
            (destination / 'evidence' / path.name).symlink_to(path)
    deploy = destination / 'target' / 'deploy'
    deploy.mkdir(parents=True)
    (deploy / 'dao_v1_recovered.so').symlink_to(binary)
    summary = {'binary': str(binary), 'sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
               'suites': [], 'passed': True}
    for suite in sorted((destination / 'scripts').glob('differential*.py')):
        with (destination / (suite.stem + '.log')).open('w') as log:
            result = subprocess.run([sys.executable, str(suite)], cwd=destination,
                                    stdout=log, stderr=subprocess.STDOUT)
        summary['suites'].append({'script': suite.name, 'exit_code': result.returncode})
        summary['passed'] &= result.returncode == 0
        print(suite.name, 'PASS' if result.returncode == 0 else 'FAIL', flush=True)
    results = []
    for path in (destination / 'evidence').glob('differential*.json'):
        results.extend(json.loads(path.read_text()))
    for path in (destination / 'evidence').glob('differential*.json.gz'):
        with gzip.open(path, 'rt') as stream:
            results.extend(json.load(stream))
    summary['cases'] = len(results)
    summary['matched_cases'] = sum(row['matches'] for row in results)
    summary['duplicate_rejection_cases'] = sum(rejected_as_duplicate(row) for row in results)
    summary['passed'] &= (bool(results) and summary['matched_cases'] == summary['cases']
                          and summary['duplicate_rejection_cases'] == 0)
    (destination / 'variant-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
