#!/usr/bin/env python3
"""Prepare the pinned candidate, run the portable validation, and zip evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
PATCH = ROOT / 'candidate.patch'
PATCH_SHA = ROOT / 'candidate.patch.sha256'
BASE_SHA = '9b9aa95848b7dbee6ba13415c3615671d4445862'
UPSTREAM = 'https://github.com/avenoxai/avenoxbeyin.git'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_patch_digest():
    return PATCH_SHA.read_text(encoding='utf-8').split()[0].lower()


def canonical_patch_bytes():
    """Accept an exact patch or the sole CRLF conversion made by Windows Git."""
    expected = expected_patch_digest()
    raw = PATCH.read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected:
        return raw, False
    normalized = raw.replace(b'\r\n', b'\n')
    if hashlib.sha256(normalized).hexdigest() == expected:
        return normalized, True
    raise ValueError('candidate.patch hash mismatch; change is not only CRLF normalization')


def execute(command, cwd, log, env=None):
    started = time.monotonic()
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, encoding='utf-8',
                               errors='backslashreplace', stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    log.write_text('$ ' + ' '.join(map(str, command)) + '\n\n' + completed.stdout,
                   encoding='utf-8')
    return {'command': list(map(str, command)), 'exit_code': completed.returncode,
            'seconds': round(time.monotonic() - started, 3), 'log': log.name}


def git_text(source, *args):
    return subprocess.run(['git', '-C', str(source), *args], check=True, text=True,
                          encoding='utf-8', errors='backslashreplace',
                          capture_output=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default=UPSTREAM,
                        help='Git source used only to prepare the pinned checkout')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11 veya daha yeni bir sürüm gerekli.')
    if not PATCH.is_file() or not PATCH_SHA.is_file():
        raise SystemExit('candidate.patch veya hash dosyası bulunamadı; depoyu yeniden indirin.')
    if shutil.which('git') is None:
        raise SystemExit('Git bulunamadı; platform README dosyasındaki kurulum adımını çalıştırın.')

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    system = platform.system().lower() or 'unknown'
    results = ROOT / 'results' / f'{system}-{stamp}'
    results.mkdir(parents=True)
    summary = {
        'schema': 1,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'platform': platform.platform(),
        'python': platform.python_version(),
        'python_executable': sys.executable,
        'git': subprocess.run(['git', '--version'], check=True, text=True,
                              capture_output=True).stdout.strip(),
        'upstream': args.source,
        'base_sha': BASE_SHA,
        'candidate_patch_sha256': expected_patch_digest(),
        'commands': [],
    }
    exit_code = 1
    try:
        with tempfile.TemporaryDirectory(prefix='beyin-platform-validation-',
                                         ignore_cleanup_errors=True) as temporary:
            patch_bytes, normalized = canonical_patch_bytes()
            canonical_patch = Path(temporary) / 'candidate.patch'
            canonical_patch.write_bytes(patch_bytes)
            summary['candidate_patch_checkout_sha256'] = digest(PATCH)
            summary['candidate_patch_crlf_normalized'] = normalized
            source = Path(temporary) / 'source'
            prepare = execute(['git', '-c', 'core.autocrlf=false', 'clone', '--quiet',
                               '--no-checkout', args.source, str(source)], ROOT,
                              results / '00-clone.log')
            summary['commands'].append(prepare)
            if prepare['exit_code']:
                raise RuntimeError('upstream clone failed')
            configure = execute(['git', 'config', 'core.autocrlf', 'false'], source,
                                results / '00-config-autocrlf.log')
            summary['commands'].append(configure)
            if configure['exit_code']:
                raise RuntimeError('cannot disable autocrlf in source checkout')
            configure_eol = execute(['git', 'config', 'core.eol', 'lf'], source,
                                    results / '00-config-eol.log')
            summary['commands'].append(configure_eol)
            if configure_eol['exit_code']:
                raise RuntimeError('cannot select LF in source checkout')
            execute(['git', 'checkout', '--quiet', BASE_SHA], source,
                    results / '00-checkout.log')
            actual = git_text(source, 'rev-parse', 'HEAD')
            if actual != BASE_SHA:
                raise RuntimeError(f'base mismatch: {actual}')
            check = execute(['git', 'apply', '--check', str(canonical_patch)], source,
                            results / '00-patch-check.log')
            summary['commands'].append(check)
            if check['exit_code']:
                raise RuntimeError('candidate patch does not apply')
            applied = execute(['git', 'apply', str(canonical_patch)], source,
                              results / '00-patch-apply.log')
            summary['commands'].append(applied)
            if applied['exit_code']:
                raise RuntimeError('candidate patch application failed')

            (results / 'patched-status.txt').write_text(git_text(source, 'status', '--short') + '\n',
                                                        encoding='utf-8')
            (results / 'patched-diff.stat.txt').write_text(git_text(source, 'diff', '--stat') + '\n',
                                                           encoding='utf-8')
            compact = source / 'template/.claude/scripts/beyin_v3_compact.py'
            summary['patched_compact_sha256'] = digest(compact)

            environment = os.environ.copy()
            environment.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
                               PYTHONDONTWRITEBYTECODE='1')
            commands = [
                ('01-probe.log', [sys.executable, str(ROOT / 'compact_probe.py'), str(source)]),
                ('02-companion.log', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                                      '-p', 'v3_companion_*test.py']),
                ('03-product.log', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                                    '-p', 'v3_product_test.py']),
                ('04-stdlib.log', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                                   '-p', 'v3_stdlib_imports_test.py']),
            ]
            for log_name, command in commands:
                print(f'Çalışıyor: {log_name}', flush=True)
                result = execute(command, source, results / log_name, environment)
                summary['commands'].append(result)
                print(f'  exit={result["exit_code"]}, süre={result["seconds"]}s', flush=True)
            exit_code = 0 if all(item['exit_code'] == 0 for item in summary['commands']) else 1
    except BaseException as exc:
        summary['runner_error'] = f'{type(exc).__name__}: {exc}'
        print(summary['runner_error'], file=sys.stderr)
    finally:
        summary['passed'] = exit_code == 0
        (results / 'summary.json').write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        archive_base = ROOT / f'validation-result-{system}-{stamp}'
        archive = Path(shutil.make_archive(str(archive_base), 'zip', results))
        print()
        print('VALIDATION PASSED' if exit_code == 0 else 'VALIDATION FAILED')
        print(f'Sonuç ZIP: {archive}')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
