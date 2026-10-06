#!/usr/bin/env python3
"""Portable runner: --candidate main=/path/to/checkout --output /path/to/results."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

CASES = ('same_payload', 'replacement', 'conflict_copy', 'git_add_add', 'inplace_changed', 'inplace_same')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', action='append', required=True, help='label=checkout')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeat', type=int, default=2)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat must be positive')
    # Refuse accidental overwriting of previous evidence.
    args.output.mkdir(parents=True, exist_ok=False)
    probe = Path(__file__).with_name('receipt_probe.py')
    rows = []
    for entry in args.candidate:
        label, checkout = entry.split('=', 1)
        for case in CASES:
            for repeat in range(1, args.repeat + 1):
                try:
                    proc = subprocess.run([sys.executable, str(probe), '--repo', checkout, '--case', case],
                                          capture_output=True, text=True, timeout=45)
                    result = json.loads(proc.stdout)
                    if proc.returncode not in (0, 1, 2):
                        result['coverage_error'] = 'unexpected process exit'
                    result['exit_code'] = proc.returncode
                except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
                    result = {'coverage_error': type(exc).__name__, 'exit_code': 2}
                result.update(candidate=label, case=case, repeat=repeat)
                rows.append(result)
                print(label, case, repeat, result['exit_code'])
    (args.output / 'cases.jsonl').write_text(''.join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')
    manifest = {'platform': platform.platform(), 'python': platform.python_version(),
                'probe_sha256': hashlib.sha256(probe.read_bytes()).hexdigest(),
                'runs': len(rows), 'coverage_errors': sum(bool(r.get('coverage_error')) for r in rows),
                'violating_runs': sum(any(v is False for v in r.get('invariants', {}).values()) for r in rows),
                'candidates': {r['candidate']: r.get('candidate_sha') for r in rows}}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return 2 if manifest['coverage_errors'] else 1 if manifest['violating_runs'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
