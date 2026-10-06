#!/usr/bin/env python3
"""Independent two-vault receipt probe. Each invocation loads one pinned candidate.

Exit 0: measured invariants hold; 1: product observation violates the proposed
acceptance contract; 2: coverage/setup error. No real user vault is opened.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(vault, *args, check=True):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0')
    return subprocess.run(['git', '-c', 'user.name=Synthetic Tester',
                           '-c', 'user.email=synthetic@example.invalid',
                           '-c', 'core.autocrlf=false', '-C', str(vault), *args],
                          env=env, capture_output=True, text=True, timeout=15, check=check)


def visible(report, source):
    return report['status'] in ('degraded', 'conflict') and any(
        item.get('source') == source
        for item in report.get('warnings', []) + report.get('conflicts', []))


def snapshot(engine):
    with engine.store._connect() as db:
        events = {key: json.loads(payload) for key, payload in
                  db.execute('SELECT id,payload FROM receipts')}
        sources = [row[0] for row in db.execute('SELECT source FROM markdown_sources ORDER BY source')]
    projections = {str(p.relative_to(engine.root)): digest(p.read_bytes())
                   for folder in ('daily/v3', 'knowledge/v3')
                   for p in (engine.root / folder).rglob('*.md')}
    return {'events': events, 'sources': sources, 'projections': projections}


def probe(repo, case):
    scripts = repo / 'template/.claude/scripts'
    sys.path.insert(0, str(scripts))
    sys.dont_write_bytecode = True
    from beyin_v3_sync import SyncEngine
    with tempfile.TemporaryDirectory(prefix='sync-receipt-probe-') as tmp:
        root = Path(tmp)
        engines = []
        git_transport = case == 'git_add_add'
        for device, payload in (('a', 'PAYLOAD_A_MUST_SURVIVE'), ('b', 'PAYLOAD_B_MUST_SURVIVE')):
            vault = root / device / 'vault'
            if git_transport and device == 'b':
                vault.parent.mkdir(parents=True)
                git(root, 'clone', '--branch', 'fixture-base', str(engines[0].root), str(vault))
                git(vault, 'checkout', '-b', 'fixture-b')
            else:
                (vault / 'notes').mkdir(parents=True)
                (vault / 'notes/source.md').write_text('Synthetic source only.\n', encoding='utf-8')
            if git_transport and device == 'a':
                git(vault, 'init', '-b', 'fixture-a')
                git(vault, 'add', 'notes/source.md')
                git(vault, 'commit', '-m', 'Synthetic shared base')
                git(vault, 'branch', 'fixture-base')
            engine = SyncEngine(vault, root / device / 'state')
            engine.receipt('synthetic-shared-event', payload, ['notes/source.md'], 'manual')
            engine.sync()
            if git_transport:
                git(vault, 'add', 'receipts')
                git(vault, 'commit', '-m', 'Synthetic independent receipt ' + device)
            engines.append(engine)
        a, b = engines
        source = 'receipts/' + digest(b'synthetic-shared-event') + '.md'
        initial = snapshot(a)
        original = (a.root / source).read_bytes()
        incoming = (b.root / source).read_bytes()
        if case == 'same_payload':
            incoming = original
        transport_evidence = None
        if git_transport:
            git(a.root, 'fetch', str(b.root), 'fixture-b')
            merge = git(a.root, 'merge', '--no-edit', 'FETCH_HEAD', check=False)
            unresolved = git(a.root, 'diff', '--name-only', '--diff-filter=U').stdout.splitlines()
            if merge.returncode != 1 or unresolved != [source]:
                raise RuntimeError('expected exactly one receipt add/add merge conflict')
            target = a.root / source
            marker_present = b'<<<<<<<' in target.read_bytes()
            target.write_bytes(incoming)
            git(a.root, 'add', source)
            git(a.root, 'commit', '-m', 'Resolve synthetic receipt by choosing device B')
            transport_evidence = {'merge_exit': merge.returncode, 'unmerged_sources': unresolved,
                                  'marker_present': marker_present,
                                  'resolved_to_incoming': target.read_bytes() == incoming}
            if not marker_present:
                raise RuntimeError('merge did not produce conflict markers')
        elif case == 'conflict_copy':
            target = a.root / source.replace('.md', ' 2.md')
            target.write_bytes(incoming)
            note_copy = a.root / 'notes/source (conflicted copy).md'
            note_copy.write_text('CONFLICT_COPY_MUST_REMAIN_VISIBLE\n', encoding='utf-8')
        else:
            target = a.root / source
            staging = target.with_suffix('.incoming')
            staging.write_bytes(incoming)
            os.replace(staging, target)
        # Freeze receipt-directory age so both scans exercise their warm-cache
        # signature optimization without sleeps. Entry replacement is explicit.
        os.utime(a.root / 'receipts', (1_700_000_000, 1_700_000_000))
        first = a.sync()
        after = snapshot(a)
        second = a.sync()
        final = snapshot(a)
        changed = case in ('replacement', 'git_add_add')
        db_changed = initial['events'] != after['events']
        invariants = {
            'S2': not changed or not db_changed or visible(first, source),
            'S3': first['status'] != 'succeeded' or case == 'conflict_copy' or
                  after['events']['synthetic-shared-event'] == a._receipt_event(source),
            'S4': not changed or visible(first, source),
            'S5': None,
            'S6': after == final and first['status'] == second['status'],
            'S10': first['status'] in ('succeeded', 'degraded', 'conflict') and
                   second['status'] in ('succeeded', 'degraded', 'conflict'),
        }
        if case == 'same_payload':
            invariants['positive_control'] = first['status'] == 'succeeded' and after == initial
        if case == 'conflict_copy':
            copy_source = target.relative_to(a.root).as_posix()
            note_source = note_copy.relative_to(a.root).as_posix()
            invariants['S5'] = (target.read_bytes() == incoming and note_copy.is_file() and
                                copy_source not in after['sources'] and note_source not in after['sources'] and
                                visible(first, copy_source) and visible(first, note_source))
        def mask(value):
            return json.loads(json.dumps(value, ensure_ascii=False).replace(str(root), '$TMPDIR'))
        return mask({'case': case, 'candidate_sha': subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
            'sync_source_sha256': digest((scripts / 'beyin_v3_sync.py').read_bytes()),
            'transport': ('git_add_add_resolved_to_b' if git_transport else
                          'file_conflict_copy' if case == 'conflict_copy' else 'resolved_replace_model'),
            'transport_evidence': transport_evidence,
            'first': first, 'second': second, 'initial': initial, 'after': after,
            'invariants': invariants, 'coverage_error': None,
            'original_receipt_sha256': digest(original), 'incoming_receipt_sha256': digest(incoming)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--case', choices=('same_payload', 'replacement', 'conflict_copy', 'git_add_add'), required=True)
    args = parser.parse_args()
    try:
        result = probe(args.repo.resolve(), args.case)
    except Exception as exc:
        print(json.dumps({'case': args.case, 'coverage_error': f'{type(exc).__name__}: {exc}'}))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return int(any(value is False for value in result['invariants'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
