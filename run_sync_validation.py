#!/usr/bin/env python3
"""Fetch pinned sync candidates, run synthetic probes, produce a shareable ZIP."""
import argparse
from evidence_redaction import redact_evidence
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile
from sync.run_probes import CASES
from sync import mutants

ROOT = Path(__file__).resolve().parent
CANDIDATES = {'main': '9b9aa95848b7dbee6ba13415c3615671d4445862',
              'pr210': 'bf7f993ffc90085cd5c430098e537bab72ddf8f6'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-checkout', type=Path)
    parser.add_argument('--pr210-checkout', type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / ('sync-validation-' + stamp)
    output.mkdir()
    summary = {'platform': platform.platform(), 'python': platform.python_version(),
               'candidates': CANDIDATES, 'status': 'setup_failed'}
    code = 2
    with tempfile.TemporaryDirectory(prefix='beyin-sync-platform-') as tmp:
        def safe(text):
            for path, replacement in ((str(Path.home()), '$HOME'), (tmp, '$TMPDIR')):
                text = text.replace(path, replacement)
                text = text.replace(path.replace('\\', '/'), replacement)
            return redact_evidence(text, roots=(ROOT,))
        try:
            paths = {}
            for name, sha in CANDIDATES.items():
                supplied = getattr(args, name + '_checkout')
                checkout = supplied.resolve() if supplied else Path(tmp) / name
                if not supplied:
                    checkout.mkdir()
                    for command in (['git', 'init', str(checkout)],
                                    ['git', '-C', str(checkout), 'fetch', '--depth=1',
                                     'https://github.com/avenoxai/avenoxbeyin.git', sha],
                                    ['git', '-C', str(checkout), 'checkout', '--detach', 'FETCH_HEAD']):
                        subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
                actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
                if actual != sha:
                    raise ValueError('candidate SHA mismatch: ' + name)
                paths[name] = checkout
            patch = ROOT / 'sync/receipt-visibility.patch'
            patch_sha = hashlib.sha256(patch.read_bytes()).hexdigest()
            if patch_sha != patch.with_suffix('.patch.sha256').read_text().strip():
                raise ValueError('candidate patch hash mismatch')
            fixed = Path(tmp) / 'fixed'
            subprocess.run(['git', 'clone', '--no-hardlinks', str(paths['pr210']), str(fixed)],
                           check=True, capture_output=True, text=True, timeout=60)
            subprocess.run(['git', '-C', str(fixed), 'checkout', '--detach', CANDIDATES['pr210']],
                           check=True, capture_output=True, text=True, timeout=30)
            subprocess.run(['git', '-C', str(fixed), 'apply', '--check', str(patch)],
                           check=True, capture_output=True, text=True, timeout=30)
            subprocess.run(['git', '-C', str(fixed), 'apply', str(patch)],
                           check=True, capture_output=True, text=True, timeout=30)
            paths['fixed'] = fixed
            mutant_paths, mutant_manifest = mutants.create(fixed, Path(tmp))
            paths.update(mutant_paths)
            (output / 'mutants.json').write_text(json.dumps(mutant_manifest, indent=2) + '\n', encoding='utf-8')
            summary['fixed_base_sha'] = CANDIDATES['pr210']
            summary['fixed_patch_sha256'] = patch_sha
            product = subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                                      '-s', 'tests', '-p', 'v3_sync_test.py'], cwd=fixed,
                                     capture_output=True, text=True, timeout=120)
            (output / 'fixed-product-tests.log').write_text(safe(product.stdout + product.stderr), encoding='utf-8')
            summary['fixed_product_tests_exit'] = product.returncode
            command = [sys.executable, str(ROOT / 'sync/run_probes.py'), '--output', str(output / 'results')]
            for name, checkout in paths.items():
                command += ['--candidate', name + '=' + str(checkout)]
            proc = subprocess.run(command, capture_output=True, text=True, timeout=900)
            (output / 'runner.log').write_text(safe(proc.stdout + proc.stderr), encoding='utf-8')
            if proc.returncode not in (0, 1, 2):
                raise RuntimeError('unexpected runner exit')
            manifest = json.loads((output / 'results/manifest.json').read_text(encoding='utf-8'))
            summary.update(manifest)
            rows = [json.loads(line) for line in
                    (output / 'results/cases.jsonl').read_text(encoding='utf-8').splitlines()]
            fixed_rows = [r for r in rows if r['candidate'] == 'fixed']
            fixed_failed = sum(any(v is False for v in r.get('invariants', {}).values()) for r in fixed_rows)
            mutation_results = mutants.evaluate(rows)
            summary['mutation_results'] = mutation_results
            mutation_failed = not all(r['designated_kill_verified'] for r in mutation_results.values())
            summary['fixed_violating_runs'] = fixed_failed
            expected = {(case, repeat) for case in CASES for repeat in (1, 2)}
            observed = {(r['case'], r['repeat']) for r in fixed_rows}
            summary['status'] = ('coverage_failed' if manifest['coverage_errors'] or observed != expected or len(fixed_rows) != len(expected) else
                                 'fixed_candidate_failed' if fixed_failed or product.returncode else
                                 'mutation_gate_failed' if mutation_failed else
                                 'fixed_candidate_passed')
            details = ['## Multi-device sync probe results', '',
                       'main/pr210 are historical comparisons. The acceptance gate checks the patched fixed candidate; baseline failures remain in this report.', '',
                       '| Candidate | Case | Repeat | Failed checks | Coverage error |',
                       '| --- | --- | ---: | --- | --- |']
            for row in rows:
                failed = ', '.join(k for k, value in row.get('invariants', {}).items() if value is False)
                details.append('| ' + ' | '.join((row['candidate'], row['case'], str(row['repeat']),
                                                 failed or 'none', row.get('coverage_error') or 'none')) + ' |')
                if failed or row.get('coverage_error'):
                    print(row['candidate'], row['case'], 'repeat', row['repeat'],
                          'failed checks:', failed or 'none', 'coverage:', row.get('coverage_error') or 'none')
            details += ['', 'S2: event content change visibility; S3: disk/SQLite agreement; '
                        'S4: source-specific divergence warning; S5: conflict-copy quarantine.', '',
                        'Node runtime/runner notices are separate from these measured receipt contract failures.']
            details += ['', '## Negative-control sensitivity', '',
                        '| Mutant | Killed runs | Designated invariant caught twice |',
                        '| --- | ---: | --- |']
            for name, result in mutation_results.items():
                details.append(f"| {name} | {result['killed_runs']} | {result['designated_kill_verified']} |")
            report = '\n'.join(details) + '\n'
            (output / 'REPORT.md').write_text(report, encoding='utf-8')
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as handle:
                    handle.write(report)
            code = (2 if summary['status'] == 'coverage_failed' else
                    1 if summary['status'] in ('fixed_candidate_failed', 'mutation_gate_failed') else 0)
        except Exception as exc:
            summary['error'] = safe(f'{type(exc).__name__}: {exc}')
            if isinstance(exc, subprocess.CalledProcessError):
                summary['detail'] = safe(exc.stderr or '')
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    archive = output.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as handle:
        for path in output.rglob('*'):
            if path.is_file():
                handle.write(path, path.relative_to(output))
    print('SYNC VALIDATION:', summary['status'])
    print('Evidence ZIP:', archive.name)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
