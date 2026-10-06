#!/usr/bin/env python3
"""Main-only semantic receipt acceptance gate; historical sync harness is preserved."""
import argparse
from evidence_redaction import redact_evidence
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
BASE = '9b9aa95848b7dbee6ba13415c3615671d4445862'
SOURCE = Path('template/.claude/scripts/beyin_v3_sync.py')
TARGETS = {'full_payload_compare': {'test_created_at_metadata', 'test_session_metadata', 'test_harness_metadata'},
           'skip_existing_receipts': {'test_summary_conflict', 'test_refs_conflict'},
           'always_succeeded': {'test_summary_conflict', 'test_refs_conflict'}}


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, timeout=120, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main-checkout', type=Path)
    args = parser.parse_args()
    output = ROOT / ('semantic-validation-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir()
    summary = {'base_sha': BASE, 'platform': platform.platform(), 'python': platform.python_version(), 'status': 'setup_failed', 'runs': []}
    code = 2
    try:
        with tempfile.TemporaryDirectory(prefix='semantic-validation-') as td:
            base = args.main_checkout.resolve() if args.main_checkout else Path(td)/'main'
            if not args.main_checkout:
                for cmd in (['git','init',str(base)], ['git','-C',str(base),'fetch','--depth=1','https://github.com/avenoxai/avenoxbeyin.git',BASE], ['git','-C',str(base),'checkout','--detach','FETCH_HEAD']):
                    run(cmd).check_returncode()
            if run(['git','-C',str(base),'rev-parse','HEAD']).stdout.strip() != BASE:
                raise ValueError('base SHA mismatch')
            run(['git','-C',str(base),'diff','--quiet','HEAD','--','template/.claude/scripts','tests']).check_returncode()
            fixed = Path(td)/'fixed'
            run(['git','clone','--no-hardlinks',str(base),str(fixed)]).check_returncode()
            patch = ROOT/'sync/semantic/main-semantic.patch'
            summary['patch_sha256'] = hashlib.sha256(patch.read_bytes()).hexdigest()
            if summary['patch_sha256'] != patch.with_suffix('.patch.sha256').read_text().strip():
                raise ValueError('patch digest mismatch')
            run(['git','-C',str(fixed),'apply','--check',str(patch)]).check_returncode()
            run(['git','-C',str(fixed),'apply',str(patch)]).check_returncode()
            product = run([sys.executable,'-m','unittest','discover','-s','tests','-p','v3_sync_test.py'],cwd=fixed)
            (output/'product-tests.log').write_text(redact_evidence(product.stdout+product.stderr, roots=(ROOT,)),encoding='utf-8')
            summary['product_exit'] = product.returncode
            candidates = {'main': base, 'fixed': fixed}
            original = (fixed/SOURCE).read_text(encoding='utf-8')
            for name in TARGETS:
                clone = Path(td)/name
                run(['git','clone','--no-hardlinks',str(base),str(clone)]).check_returncode()
                changed = original
                if name == 'full_payload_compare':
                    old = "if previous[field] != event[field]]"
                    new = "if previous != event]"
                elif name == 'skip_existing_receipts':
                    old = "                if row:\n                    previous = json.loads(row[0])"
                    new = "                if row:\n                    continue\n                    previous = json.loads(row[0])"
                else:
                    old = "'status': 'conflict' if conflicts else 'degraded' if warnings else 'succeeded'"
                    new = "'status': 'succeeded'"
                if changed.count(old) != 1:
                    raise ValueError('mutation anchor mismatch: '+name)
                changed = changed.replace(old,new,1)
                compile(changed,'<mutant>','exec')
                (clone/SOURCE).write_text(changed,encoding='utf-8',newline='')
                candidates[name] = clone
            for name, candidate in candidates.items():
                for repeat in (1,2):
                    proc = run([sys.executable,str(ROOT/'sync/semantic/run_suite.py')],env=dict(os.environ,SYNC_CANDIDATE=str(candidate)))
                    data = json.loads(proc.stdout)
                    data.update(candidate=name,repeat=repeat,exit=proc.returncode,
                                source_sha256=hashlib.sha256((candidate/SOURCE).read_bytes()).hexdigest())
                    summary['runs'].append(data)
            coverage = all(r['tests']==8 and not r['errors'] and r['exit'] in (0,1) for r in summary['runs'])
            fixed_ok = all(r['exit']==0 for r in summary['runs'] if r['candidate']=='fixed') and product.returncode==0
            baseline_ok = all(set(r['failures'])==TARGETS['skip_existing_receipts'] for r in summary['runs'] if r['candidate']=='main')
            kills = {name: all(r['exit']==1 and not r['errors'] and targets.issubset(r['failures']) for r in summary['runs'] if r['candidate']==name) for name,targets in TARGETS.items()}
            summary['mutation_kills'] = kills
            summary['status'] = 'passed' if coverage and fixed_ok and baseline_ok and all(kills.values()) else 'failed'
            code = 0 if summary['status']=='passed' else 1 if coverage else 2
    except Exception as exc:
        summary['error'] = type(exc).__name__+': '+str(exc)
    (output/'summary.json').write_text(redact_evidence(json.dumps(summary,indent=2),roots=(ROOT,))+'\n',encoding='utf-8')
    lines = ['# Main semantic receipt validation','',f"Result: **{summary['status']}**",'',f'Pinned base: `{BASE}`','',
             '| Candidate | Repeat | Tests | Assertion failures | Setup errors |','| --- | ---: | ---: | --- | --- |']
    for r in summary['runs']:
        lines.append(f"| {r['candidate']} | {r['repeat']} | {r['tests']} | {', '.join(r['failures']) or 'none'} | {', '.join(r['errors']) or 'none'} |")
    lines += ['', 'Directory mtime cache is preserved. In-place changes without directory changes are explicitly outside this candidate. Metadata differences preserve indexed metadata and are not event collisions. Full payload hashes are not semantic identity. No automatic conflict repair or distributed locking is implemented.']
    report = '\n'.join(lines)+'\n'
    (output/'REPORT.md').write_text(report,encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f: f.write(report)
    with zipfile.ZipFile(output.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
        for p in output.rglob('*'):
            if p.is_file(): z.write(p,p.relative_to(output))
    print(summary['status'],output.name)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
