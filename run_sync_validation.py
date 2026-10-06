#!/usr/bin/env python3
"""Fetch pinned sync candidates, run synthetic probes, produce a shareable ZIP."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

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
            return text
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
            command = [sys.executable, str(ROOT / 'sync/run_probes.py'), '--output', str(output / 'results')]
            for name, checkout in paths.items():
                command += ['--candidate', name + '=' + str(checkout)]
            proc = subprocess.run(command, capture_output=True, text=True, timeout=900)
            (output / 'runner.log').write_text(safe(proc.stdout + proc.stderr), encoding='utf-8')
            if proc.returncode not in (0, 1, 2):
                raise RuntimeError('unexpected runner exit')
            manifest = json.loads((output / 'results/manifest.json').read_text(encoding='utf-8'))
            summary.update(manifest)
            summary['status'] = ('coverage_failed' if manifest['coverage_errors'] else
                                 'contract_violations' if manifest['violating_runs'] else 'passed')
            code = proc.returncode
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
