#!/usr/bin/env python3
"""Phase 1/3: single-pause interleaving sweep, invariant oracle, mutation analysis.

No historical boolean expectations are read. Each actor is a fresh spawn process.
Only Last-Session.md and its monthly archive reads/writes/unlinks are traced.
This is a bounded schedule exploration, NOT all possible thread interleavings.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import difflib
import hashlib
import io
import itertools
import json
import linecache
import multiprocessing as mp
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPT_DIR = Path('template/.claude/scripts')
COMPACT = SCRIPT_DIR / 'beyin_v3_compact.py'
NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
OLD = 'OLD_CARD_CONTENT_MUST_REMAIN_RECOVERABLE'
NEWEST = 'NEWEST_CARD_CONTENT'
EXISTING = '# EXISTING_ARCHIVE_MARKER\n'
OLD_CARD = '## 2026-09-01 09:00 · eski · a\n' + OLD + '\n' + 'eski veri ' * 300 + '\n\n'
FIXTURE = '# Son oturum\n\n' + OLD_CARD + '## 2026-09-02 09:00 · yeni · b\n' + NEWEST + '\n' + 'yeni veri ' * 300 + '\n'
ALLOWED = {'compacted', 'conflict', 'needs_rewrite', 'within_limit'}
HISTORICAL = [
    ('v3.7.1', 'audit-v2/runs/20261003-141426-193930/source', '16af4bc30f0b7e6f6e810e1e1e1ac43e42811ab5'),
    ('pr194', 'fixes/compact-data-loss', '3279bb2533f96c7101771c99c9286f7ea1845d2f'),
    ('pr195', 'fixes/compact-data-loss-pr195', '1e5b168b13f3779aec8815229616ed35dcd82fa4'),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def settings():
    result = {name: float(os.environ.get(env, default)) for name, env, default in [
        ('ready', 'BEYIN_TEST_READY_TIMEOUT', '20'),
        ('probe', 'BEYIN_TEST_BLOCK_PROBE_SECONDS', '3'),
        ('join', 'BEYIN_TEST_JOIN_TIMEOUT', '25'),
    ]}
    if any(value <= 0 for value in result.values()):
        raise ValueError('All BEYIN_TEST_* timeouts must be positive')
    return result


def prepare(base, isolation):
    vault = base / 'vault'
    companion = vault / '🔮 850-Companion'
    companion.mkdir(parents=True)
    live = companion / 'Last-Session.md'
    archive = companion / 'Arşiv/Last-Session-2026-10.md'
    live.write_bytes(FIXTURE.encode('utf-8'))
    if isolation['existing_archive']:
        archive.parent.mkdir()
        archive.write_bytes(EXISTING.encode('utf-8'))
    states = [base / 'state-slow', base / ('state-fast' if isolation['split_state'] else 'state-slow')]
    temps = [base / 'tmp-slow', base / ('tmp-fast' if isolation['split_tmp'] else 'tmp-slow')]
    for state in set(states):
        state.mkdir()
        write_json(state / 'companion-limits.json', {'schema': 1, 'Last-Session.md': 3000, 'Threads.md': 8000})
    for temp in set(temps):
        temp.mkdir()
    fast_vault = vault
    if isolation['vault_alias']:
        fast_vault = base / 'vault-alias'
        fast_vault.symlink_to(vault, target_is_directory=True)
    return vault, fast_vault, states, temps, live, archive


class Hooks:
    """Read ordinals are NOT used to infer semantic names: label source call sites."""
    def __init__(self, compact, live, archive, pause_k, ready, resume, timeout):
        self.compact = compact
        self.targets = {live.resolve(): 'live', archive.resolve(): 'archive'}
        self.k, self.ready, self.resume, self.timeout = pause_k, ready, resume, timeout
        self.trace, self.depth, self.paused = [], 0, False
        self.crash_send = None
        self.read = Path.read_bytes
        self.unlink = Path.unlink
        self.write = compact._write

    def gate(self, kind, path, frame):
        if self.depth:
            return
        target = self.targets.get(Path(path).resolve())
        if target is None:
            return
        source = linecache.getline(frame.f_code.co_filename, frame.f_lineno).strip()
        name = f'{target}_{kind}_unclassified'
        if kind == 'read':
            if target == 'live':
                if 'raw = ' in source:
                    name = 'live_read_initial'
                elif 'current_live' in source:
                    name = 'live_read_prewrite'
                elif '!= raw' in source:
                    name = 'live_read_postwrite'
            else:
                if 'previous = ' in source:
                    name = 'archive_snapshot'
                elif 'current_archive' in source:
                    name = 'archive_read_prewrite'
                elif 'archive_written' in source:
                    name = 'archive_read_rollback_check'
        elif kind == 'write':
            name = 'live_write' if target == 'live' else ('archive_rollback' if 'previous' in source else 'archive_write')
        elif kind == 'unlink':
            name = 'archive_rollback' if target == 'archive' else 'live_unlink'
        event = {'k': len(self.trace) + 1, 'name': name, 'kind': kind, 'target': target,
                 'line': frame.f_lineno, 'source': source}
        self.trace.append(event)
        if event['k'] == self.k:
            self.paused = True
            self.ready.set()
            if self.crash_send is not None:
                self.crash_send.send({'trace': self.trace, 'paused': True, 'deliberate_crash': True})
                self.crash_send.close()
                os._exit(17)
            if not self.resume.wait(self.timeout):
                raise RuntimeError('harness resume deadline exceeded')

    def __enter__(self):
        def read(path):
            self.gate('read', path, sys._getframe(1))
            return self.read(path)

        def write(path, content):
            self.gate('write', path, sys._getframe(1))
            self.depth += 1
            try:
                return self.write(path, content)
            finally:
                self.depth -= 1

        def unlink(path, *args, **kwargs):
            self.gate('unlink', path, sys._getframe(1))
            return self.unlink(path, *args, **kwargs)

        Path.read_bytes, self.compact._write, Path.unlink = read, write, unlink
        return self

    def __exit__(self, *exc):
        Path.read_bytes, self.compact._write, Path.unlink = self.read, self.write, self.unlink


def actor(repo, vault, state, temp, instrument, pause_k, events, send, limits):
    """Fast actor calls compact directly; no file-operation wrappers are installed."""
    ready, resume, started, done = events
    sys.dont_write_bytecode = True
    tempfile.tempdir = str(temp)
    sys.path.insert(0, str(Path(repo) / SCRIPT_DIR))
    hooks = None
    payload = {}
    start = time.monotonic()
    try:
        import beyin_v3_compact as compact
        started.set()
        if instrument:
            companion = Path(vault).resolve() / '🔮 850-Companion'
            hooks = Hooks(compact, companion / 'Last-Session.md', companion / 'Arşiv/Last-Session-2026-10.md',
                          pause_k, ready, resume, limits['ready'] + limits['probe'] + limits['join'])
            hooks.crash_send = send if limits.get('crash') and pause_k else None
            with hooks:
                payload['result'] = compact.compact(vault, state, now=NOW)
        else:
            payload['result'] = compact.compact(vault, state, now=NOW)
    except BaseException:
        payload['error'] = traceback.format_exc()
    finally:
        payload.update(trace=hooks.trace if hooks else [], paused=bool(hooks and hooks.paused),
                       elapsed_seconds=time.monotonic() - start)
        try:
            send.send(payload)
        finally:
            send.close()
            done.set()


def launch(ctx, repo, vault, state, temp, instrument, k, limits):
    events = [ctx.Event() for _ in range(4)]
    receive, send = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=actor, args=(repo, vault, state, temp, instrument, k, events, send, limits))
    proc.start()
    send.close()
    return {'process': proc, 'receive': receive, 'events': events}


def collect(handle, deadline):
    proc, receive = handle['process'], handle['receive']
    payload = {}
    timed_out = False
    try:
        # Drain before join: a long trace must not block the child on a full pipe.
        if receive.poll(max(0, deadline - time.monotonic())):
            try:
                payload = receive.recv()
            except EOFError:
                payload = {'error': 'actor exited without a payload'}
        else:
            timed_out = True
        proc.join(max(0, deadline - time.monotonic()))
        if proc.is_alive():
            timed_out = True
            proc.terminate()
            proc.join(3)
            if proc.is_alive():
                proc.kill()
                proc.join(3)
        payload.update(exitcode=proc.exitcode, timed_out=timed_out)
        return payload
    finally:
        receive.close()


def cleanup(handle):
    if handle is None:
        return
    handle['events'][1].set()
    proc = handle['process']
    if proc.is_alive():
        proc.terminate()
        proc.join(3)
        if proc.is_alive():
            proc.kill()
            proc.join(3)
    handle['receive'].close()


def statuses(payload):
    result = payload.get('result', {})
    return {'overall': result.get('status'), 'file': result.get('files', {}).get('Last-Session.md', {}).get('status')}


def file_observation(live, archive):
    live_bytes = live.read_bytes() if live.exists() else b''
    archive_bytes = archive.read_bytes() if archive.exists() else b''
    return {
        'hashes': {'live': digest(live_bytes) if live.exists() else None,
                   'archive': digest(archive_bytes) if archive.exists() else None},
        'sizes': {'live': len(live_bytes), 'archive': len(archive_bytes)},
        'old_in_live': OLD.encode() in live_bytes,
        'old_in_archive': OLD.encode() in archive_bytes,
        'full_old_card_preserved': OLD_CARD.encode() in live_bytes or OLD_CARD.encode() in archive_bytes,
        'newest_preserved': NEWEST.encode() in live_bytes or NEWEST.encode() in archive_bytes,
        'existing_archive_preserved': EXISTING.encode() in archive_bytes,
    }


def oracle(observation, payloads):
    success_claims = [label for label, payload in payloads.items()
                      if 'compacted' in statuses(payload).values()]
    i3 = all(not p.get('error') and not p.get('timed_out') and p.get('exitcode') == 0
             and statuses(p)['overall'] in ALLOWED
             and (statuses(p)['file'] in ALLOWED or
                  (statuses(p)['file'] is None and statuses(p)['overall'] == 'conflict'))
             for p in payloads.values())
    # Fixture has one movable old card. A Last-Session compacted claim must retain it in archive.
    return {'I1': observation['old_in_live'] or observation['old_in_archive'],
            'I2': not success_claims or observation['old_in_archive'],
            'I3': i3, 'I4': None}, success_claims


def trace_once(candidate, existing, limits):
    iso = dict(existing_archive=existing, split_state=False, split_tmp=False, vault_alias=False)
    with tempfile.TemporaryDirectory(prefix='beyin-invariant-trace-') as temporary:
        vault, _, states, temps, live, archive = prepare(Path(temporary), iso)
        handle = launch(mp.get_context('spawn'), candidate['path'], vault, states[0], temps[0], True, None, limits)
        try:
            payload = collect(handle, time.monotonic() + limits['join'])
        finally:
            cleanup(handle)
        observation = file_observation(live, archive)
        invariants, claims = oracle(observation, {'trace': payload})
        if not all(v for v in invariants.values() if v is not None) or not payload['trace']:
            raise RuntimeError(f"invalid discovery run: {candidate['id']}: {payload}")
        return {'existing_archive': existing, 'operations': payload['trace'], 'result': payload['result'],
                'invariants': invariants, 'observation': observation}


def case_id(isolation, operation):
    return ('archive-' + ('existing' if isolation['existing_archive'] else 'new')
            + '__state-' + ('split' if isolation['split_state'] else 'shared')
            + '__tmp-' + ('split' if isolation['split_tmp'] else 'shared')
            + '__vault-' + ('alias' if isolation['vault_alias'] else 'direct')
            + '__' + (f"k{operation['k']:02d}-{operation['name']}" if operation else 'serial'))


def run_case(candidate, isolation, operation, limits):
    if limits.get('crash'):
        return run_crash_case(candidate, isolation, operation, limits)
    ctx = mp.get_context('spawn')
    start = time.monotonic()
    slow = fast = None
    payloads = {}
    coverage_errors = []
    finished_before = None
    with tempfile.TemporaryDirectory(prefix='beyin-invariant-case-') as temporary:
        vault, fast_vault, states, temps, live, archive = prepare(Path(temporary), isolation)
        try:
            slow = launch(ctx, candidate['path'], vault, states[0], temps[0], True,
                          operation['k'] if operation else None, limits)
            if operation:
                ready_deadline = time.monotonic() + limits['ready']
                while not slow['events'][0].wait(0.02):
                    if slow['events'][3].is_set() or time.monotonic() >= ready_deadline:
                        coverage_errors.append('pause_not_reached')
                        break
                if not coverage_errors:
                    fast = launch(ctx, candidate['path'], fast_vault, states[1], temps[1], False, None, limits)
                    if not fast['events'][2].wait(limits['ready']):
                        coverage_errors.append('fast_not_started')
                    finished_before = fast['events'][3].wait(limits['probe'])
                slow['events'][1].set()
                deadline = time.monotonic() + limits['join']
                payloads['slow'] = collect(slow, deadline)
                payloads['fast'] = collect(fast, deadline) if fast else {'error': 'not started', 'exitcode': None}
            else:
                payloads['slow'] = collect(slow, time.monotonic() + limits['join'])
                fast = launch(ctx, candidate['path'], fast_vault, states[1], temps[1], False, None, limits)
                payloads['fast'] = collect(fast, time.monotonic() + limits['join'])
            if operation:
                trace = payloads['slow'].get('trace', [])
                actual = trace[operation['k'] - 1] if len(trace) >= operation['k'] else None
                if actual != operation or not payloads['slow'].get('paused'):
                    coverage_errors.append('pause_operation_mismatch')
            observation = file_observation(live, archive)
            invariants, claims = oracle(observation, payloads)
            violated = [key for key, value in invariants.items() if value is False]
            return {'candidate': candidate['id'], 'case_id': case_id(isolation, operation),
                    'isolation': isolation, 'pause_before': operation, 'mode': 'pause' if operation else 'serial',
                    'actors': payloads, 'statuses': {who: statuses(p) for who, p in payloads.items()},
                    'success_claims': claims, 'observation': observation, 'invariants': invariants,
                    'violated': violated, 'invariant_passed': not violated,
                    'coverage_valid': not coverage_errors, 'coverage_errors': coverage_errors,
                    'fast_finished_before_release': finished_before,
                    'elapsed_seconds': time.monotonic() - start}
        finally:
            cleanup(slow)
            cleanup(fast)


def run_crash_case(candidate, isolation, operation, limits):
    ctx = mp.get_context('spawn')
    handles, payloads, errors = [], {}, []
    with tempfile.TemporaryDirectory(prefix='beyin-crash-case-') as temporary:
        vault, alias, states, temps, live, archive = prepare(Path(temporary), isolation)
        try:
            slow = launch(ctx, candidate['path'], vault, states[0], temps[0], True,
                          operation['k'] if operation else None, limits)
            handles.append(slow)
            crashed = collect(slow, time.monotonic() + limits['ready'] + limits['join'])
            if operation:
                if (crashed.get('exitcode') != 17 or not crashed.get('deliberate_crash')
                        or crashed.get('trace', [None])[-1] != operation):
                    errors.append('crash_operation_mismatch')
            else:
                payloads['slow'] = crashed
            before_retry = file_observation(live, archive)
            for label, path, state, temp in [('fast', alias, states[1], temps[1]),
                                             ('retry', vault, states[0], temps[0])]:
                handle = launch(ctx, candidate['path'], path, state, temp, False, None, limits)
                handles.append(handle)
                payloads[label] = collect(handle, time.monotonic() + limits['join'])
            observation = file_observation(live, archive)
            invariants, claims = oracle(observation, payloads)
            invariants['I1'] = invariants['I1'] and (before_retry['old_in_live'] or before_retry['old_in_archive'])
            violated = [key for key, value in invariants.items() if value is False]
            return {'candidate': candidate['id'], 'case_id': case_id(isolation, operation),
                    'isolation': isolation, 'pause_before': operation, 'mode': 'crash' if operation else 'serial',
                    'crashed_actor': crashed, 'before_retry': before_retry, 'actors': payloads,
                    'statuses': {who: statuses(p) for who, p in payloads.items()},
                    'success_claims': claims, 'observation': observation, 'invariants': invariants,
                    'violated': violated, 'invariant_passed': not violated,
                    'coverage_valid': not errors, 'coverage_errors': errors}
        finally:
            for handle in handles:
                cleanup(handle)


def export_source(repo, commit, target):
    # Export committed files only, never change an existing checkout or copy credentials.
    data = subprocess.run(['git', '-C', str(repo), 'archive', commit, str(SCRIPT_DIR)],
                          check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('unsafe archive member')
            if member.isdir():
                (target / path).mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                destination = target / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.extractfile(member).read())
            else:
                raise ValueError('unsupported archive member')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'mutation requires exactly one match: {old!r}')
    return text.replace(old, new, 1)


def checkout_candidates(output, repo):
    """Snapshot tracked runtime files, including the candidate's uncommitted patch."""
    repo = repo.resolve()
    commit = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                            check=True, capture_output=True, text=True).stdout.strip()
    sources = output / 'sources'
    sources.mkdir()
    base = sources / 'reference'
    export_source(repo, commit, base)
    for path in base.rglob('*'):
        if path.is_file():
            path.write_bytes((repo / path.relative_to(base)).read_bytes())
    original = (base / COMPACT).read_text(encoding='utf-8')
    mutant = replace_once(original,
                          '        with _compact_lock(target):\n            return _compact_files(vault, target, configured, dry_run=False, now=now)',
                          '        return _compact_files(vault, target, configured, dry_run=False, now=now)')
    no_lock = sources / 'mutant_no_lock'
    shutil.copytree(base, no_lock)
    (no_lock / COMPACT).write_text(mutant, encoding='utf-8')
    (sources / 'mutant_no_lock.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), mutant.splitlines(True), fromfile='candidate', tofile='no-lock')), encoding='utf-8')
    candidates = []
    for name, path, kind in [('reference', base, 'reference'), ('mutant_no_lock', no_lock, 'mutant')]:
        hashes = {p.relative_to(path).as_posix(): digest(p.read_bytes())
                  for p in sorted(path.rglob('*')) if p.is_file()}
        candidates.append({'id': name, 'path': str(path), 'kind': kind, 'base_commit': commit,
                           'checkout': str(repo), 'files_sha256': hashes,
                           'source_sha256': digest(json.dumps(hashes, sort_keys=True).encode()),
                           'compact_sha256': hashes[COMPACT.as_posix()]})
    return candidates


def make_candidates(output):
    sources = output / 'sources'
    sources.mkdir()
    candidates = []
    for name, relative, commit in HISTORICAL:
        repo = ROOT / relative
        head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'],
                              check=True, capture_output=True, text=True).stdout.strip()
        if head != commit:
            raise ValueError(f'{name}: expected {commit}, actual HEAD {head}')
        path = sources / name
        export_source(repo, commit, path)
        candidates.append({'id': name, 'kind': 'historical', 'path': str(path), 'base_commit': commit})
    base = Path(candidates[-1]['path'])
    original = (base / COMPACT).read_text(encoding='utf-8')
    reference = replace_once(original, "    lock_path = Path(state) / 'compact.lock'",
                             "    lock_path = Path(vault).resolve() / '.beyin-compact.lock'")
    versions = [('reference', reference, 'reference', 'vault lock; unchanged PR195 archive pre-write comparison')]
    mutation_specs = [
        ('mutant_no_lock',
         '        with _compact_lock(vault, state):\n            return _compact_files(vault, target, configured, dry_run=False, now=now)',
         '        return _compact_files(vault, target, configured, dry_run=False, now=now)', 'remove outer lock'),
        ('mutant_no_archive_prewrite',
         '            if current_live != raw or current_archive != previous:',
         '            if current_live != raw:', 'disable archive pre-write comparison; retain read'),
        ('mutant_no_rollback_guard',
         "                if archive.exists() and archive.read_bytes() == archive_written.encode('utf-8'):",
         "                if archive.exists():", 'remove archive ownership check on rollback'),
        ('mutant_no_live_postwrite',
         '            if path.read_bytes() != raw:',
         '            if path.read_bytes() != raw and False:', 'disable post-archive live guard; retain read'),
        ('mutant_no_live_prewrite',
         '            if current_live != raw or current_archive != previous:',
         '            if current_archive != previous:', 'disable live pre-archive guard; retain read'),
    ]
    for name, old, new, description in mutation_specs:
        versions.append((name, replace_once(reference, old, new), 'mutant', description))
    for name, text, kind, description in versions:
        path = sources / name
        shutil.copytree(base, path)
        (path / COMPACT).write_text(text, encoding='utf-8')
        parent = reference if kind == 'mutant' else original
        patch = ''.join(difflib.unified_diff(parent.splitlines(True), text.splitlines(True),
                                            fromfile='parent/beyin_v3_compact.py', tofile=name + '/beyin_v3_compact.py'))
        (sources / (name + '.patch')).write_text(patch, encoding='utf-8')
        candidates.append({'id': name, 'kind': kind, 'path': str(path), 'base_commit': HISTORICAL[-1][2],
                           'description': description, 'parent': 'reference' if kind == 'mutant' else 'pr195'})
    for candidate in candidates:
        path = Path(candidate['path'])
        candidate['files_sha256'] = {p.relative_to(path).as_posix(): digest(p.read_bytes())
                                     for p in sorted(path.rglob('*')) if p.is_file()}
        candidate['source_sha256'] = digest(json.dumps(candidate['files_sha256'], sort_keys=True).encode())
        candidate['compact_sha256'] = candidate['files_sha256'][COMPACT.as_posix()]
    return candidates


def short_case(row):
    return {key: row[key] for key in ('case_id', 'pause_before', 'isolation', 'violated', 'statuses')}


def summarize_candidate(candidate, rows, traces):
    rows = sorted(rows, key=lambda r: (tuple(r['isolation'].values()),
                                      r['pause_before']['k'] if r['pause_before'] else 0))
    violations = [row for row in rows if row['violated']]
    covered = {event['name'] for trace in traces for event in trace['operations']}
    runtime = {event['name'] for row in rows
               for event in row.get('crashed_actor', row['actors'].get('slow', {})).get('trace', [])}
    groups = defaultdict(list)
    for row in rows:
        groups[json.dumps(row['isolation'], sort_keys=True)].append(row)
    return {'candidate': candidate['id'], 'kind': candidate['kind'], 'cases': len(rows),
            'trace_lengths': {str(t['existing_archive']): len(t['operations']) for t in traces},
            'violating_cases': len(violations),
            'invariant_violations': dict(Counter(i for row in rows for i in row['violated'])),
            'coverage_errors': sum(not r['coverage_valid'] for r in rows),
            'first_violation': short_case(violations[0]) if violations else None,
            'observed_but_not_pause_seeded': sorted(runtime - covered),
            'per_isolation': [
                {'isolation': json.loads(key), 'cases': len(group),
                 'violating_cases': sum(bool(r['violated']) for r in group),
                 'first_violation': next((short_case(r) for r in group if r['violated']), None)}
                for key, group in groups.items()],
            'mutant_outcome': ('killed' if violations else 'survived_this_scope') if candidate['kind'] == 'mutant' else None}


def anchors(all_rows):
    def test(name, candidate, operation, predicate, expect_loss):
        selected = [r for r in all_rows if r['candidate'] == candidate and r['pause_before']
                    and r['pause_before']['name'] == operation and predicate(r['isolation'])]
        ok = bool(selected) and all(r['coverage_valid'] and r['invariants']['I3']
                                   and r['invariants']['I1'] == (not expect_loss) for r in selected)
        return {'anchor': name, 'candidate': candidate, 'operation': operation,
                'tested_cases': len(selected), 'compatible': ok,
                'cases': [r['case_id'] for r in selected]}
    return [
        test('original_issue193', 'v3.7.1', 'live_read_postwrite',
             lambda i: not i['split_state'] and not i['split_tmp'] and not i['vault_alias'], True),
        test('pr194_split_tmp', 'pr194', 'archive_write',
             lambda i: not i['split_state'] and i['split_tmp'] and not i['vault_alias'], True),
        test('pr195_same_state', 'pr195', 'archive_write',
             lambda i: not i['split_state'] and i['split_tmp'] and not i['vault_alias'], False),
        test('pr195_split_state', 'pr195', 'archive_write',
             lambda i: i['split_state'] and i['split_tmp'] and not i['vault_alias'], True),
        test('pr195_split_state_alias', 'pr195', 'archive_write',
             lambda i: i['split_state'] and i['split_tmp'] and i['vault_alias'], True),
    ]


def report_markdown(summary):
    lines = ['# #193 invariant taraması — Faz 1 ve 3', '',
             'Her aday kendi tek süreçli izinde görülen işlem sınırlarında duraklatıldı. '
             'Her sınır 16 izolasyon kombinasyonunda denendi; ayrıca her kombinasyonda seri kontrol koşuldu.', '',
             '| Aday | Koşu | İhlalli koşu | İlk ihlal işlemi | Invariant |',
             '| --- | ---: | ---: | --- | --- |']
    for c in summary['candidates']:
        first = c['first_violation']
        operation = first['pause_before']['name'] if first and first['pause_before'] else '—'
        lines.append(f"| {c['candidate']} | {c['cases']} | {c['violating_cases']} | {operation} | {', '.join(c['invariant_violations']) or '—'} |")
    lines += ['', '## İzolasyon başına ilk ihlal', '',
              'Hücreler ilk ihlal işlemidir; `—` bu kapsamda ihlal görülmediğini belirtir. '
              'Yol sütununda alias, ikinci aktörün aynı vault’a symlink üzerinden erişmesidir.', '']
    selected = [c for c in summary['candidates'] if c['kind'] != 'mutant' or c['candidate'] == 'mutant_no_lock']
    lines += ['| Arşiv | state | TMPDIR | Yol | ' + ' | '.join(c['candidate'] for c in selected) + ' |',
              '| --- | --- | --- | --- | ' + ' | '.join('---' for c in selected) + ' |']
    for exists, state, temp, alias in itertools.product((False, True), repeat=4):
        isolation = dict(existing_archive=exists, split_state=state, split_tmp=temp, vault_alias=alias)
        cells = ['var' if exists else 'yok', 'farklı' if state else 'aynı',
                 'farklı' if temp else 'aynı', 'alias' if alias else 'doğrudan']
        for candidate in selected:
            group = next(g for g in candidate['per_isolation'] if g['isolation'] == isolation)
            first = group['first_violation']
            cells.append(first['pause_before']['name'] if first and first['pause_before'] else '—')
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines += ['', 'Mutant sonuçları:', '', '| Mutant | Sonuç | Öldüren koşu sayısı | İlk koşu |', '| --- | --- | ---: | --- |']
    for c in summary['candidates']:
        if c['kind'] == 'mutant':
            lines.append(f"| {c['candidate']} | {c['mutant_outcome']} | {c['violating_cases']} | {c['first_violation']['case_id'] if c['first_violation'] else '—'} |")
    lines += ['', 'Hayatta kalanlar: ' + ', '.join(summary['survivors']) + '.', '',
              'Hayatta kalmak, korumanın genel olarak gereksiz olduğunu kanıtlamaz. '
              'Bu taramada dış yazar yoktur ve mutantların dördü ortak vault kilidini korur. '
              'I4 bu yüzden uygulanmaz (`null`).', '',
              'Tarama tek bir işlem öncesinde duraklatır; bütün interleaving uzayının model kontrolü değildir. '
              'Tek süreçli başlangıç izi conflict/rollback dallarını ziyaret etmeyebilir. '
              'Çalışırken görülüp duraklatma tohumu olmayan işlemler özet JSON içinde ayrıca listelenir.', '',
              'Faz 2 (çökme/yeniden deneme), Faz 4 (dış yazar), Windows ve macOS bu koşuda çalıştırılmadı. '
              'Linux symlink testi canonical yol birleştirmesini sınar; macOS doğrulaması sayılmaz.', '',
              'Referansın arşiv kontrolü PR195’teki ayrı oku/karşılaştır/yaz dizisidir; atomik CAS değildir. '
              'Canlı yazım öncesi bağımsız ek kontrol bulunmadığından son mutant, mevcut '
              '`current_live != raw` pre-write koşulunu kaldırır. Yazım sonrası kontrol ayrı mutanttır.', '',
              'Özet: [summary.json](summary.json). Ayrıntılı koşular: [cases.jsonl](cases.jsonl). '
              'İzler: [traces.json](traces.json). Kaynaklar ve mutant diff’leri: `sources/`.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='new output directory; never overwrite a run')
    parser.add_argument('--jobs', type=int, default=4, help='concurrent independent test cases')
    parser.add_argument('--candidate', action='append', help='candidate id to run; default all historical/ref/mutants')
    parser.add_argument('--checkout', type=Path, help='test a working-tree candidate and its no-lock mutant')
    parser.add_argument('--crash', action='store_true', help='exit at each boundary, then compact and retry')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if sys.platform != 'linux' or platform.python_version() != '3.12.3':
        parser.error('this validated profile requires Linux / Python 3.12.3')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    limits = settings()
    limits['crash'] = args.crash
    start = time.monotonic()
    candidates = checkout_candidates(output, args.checkout) if args.checkout else make_candidates(output)
    if args.crash:
        candidates = [c for c in candidates if c['kind'] != 'mutant']
    if args.candidate:
        known = {c['id'] for c in candidates}
        if set(args.candidate) - known:
            parser.error('unknown candidate')
        candidates = [c for c in candidates if c['id'] in args.candidate]
    run_info = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'environment': {'platform': platform.platform(), 'python': platform.python_version(),
                                'start_method': 'spawn', 'case_executor': 'ProcessPoolExecutor',
                                'jobs': args.jobs, 'timeouts_seconds': limits},
                'harness_sha256': digest(Path(__file__).read_bytes()),
                'fixture': {'sha256': digest(FIXTURE.encode()), 'chars': len(FIXTURE),
                            'old_card_chars': len(OLD_CARD), 'time_utc': NOW.isoformat(),
                            'limits': {'Last-Session.md': 3000, 'Threads.md': 8000}},
                'candidates': candidates}
    write_json(output / 'run.json', run_info)
    all_rows, summaries, traces = [], [], {}
    with (output / 'cases.jsonl').open('x', encoding='utf-8') as journal:
        for candidate in candidates:
            name = candidate['id']
            discovered = [trace_once(candidate, exists, limits) for exists in (False, True)]
            traces[name] = discovered
            write_json(output / 'traces.json', traces)
            jobs = []
            for exists, state, temp, alias in itertools.product((False, True), repeat=4):
                isolation = dict(existing_archive=exists, split_state=state, split_tmp=temp, vault_alias=alias)
                operations = discovered[int(exists)]['operations']
                jobs.extend((isolation, operation) for operation in [None, *operations])
            print(f"{name}: trace N={[len(t['operations']) for t in discovered]}, cases={len(jobs)}", flush=True)
            rows = []
            # Each case owner has its own multiprocessing child registry. Concurrent
            # thread owners can race in Process.start()'s global child cleanup/poll.
            with ProcessPoolExecutor(max_workers=args.jobs, mp_context=mp.get_context('spawn')) as pool:
                futures = [pool.submit(run_case, candidate, isolation, op, limits) for isolation, op in jobs]
                for future in as_completed(futures):
                    row = future.result()
                    rows.append(row)
                    journal.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
                    journal.flush()
                    if len(rows) % 32 == 0:
                        print(f"  {name}: {len(rows)}/{len(jobs)}", flush=True)
            all_rows.extend(rows)
            result = summarize_candidate(candidate, rows, discovered)
            summaries.append(result)
            print(f"{name}: violations={result['violating_cases']}, coverage_errors={result['coverage_errors']}", flush=True)
    checks = anchors(all_rows) if len(candidates) == 9 else []
    reference = next((c for c in summaries if c['candidate'] == 'reference'), None)
    no_lock = next((c for c in summaries if c['candidate'] == 'mutant_no_lock'), None)
    summary = {'schema_version': 1, 'phases': [1, 3], 'scope': 'single-pause two-actor operation-boundary sweep',
               'case_count': len(all_rows), 'elapsed_seconds': time.monotonic() - start,
               'candidates': summaries, 'anchors': checks,
               'survivors': [c['candidate'] for c in summaries if c['mutant_outcome'] == 'survived_this_scope'],
               'reference_no_violations': bool(reference and reference['violating_cases'] == 0 and not reference['coverage_errors']),
               'lock_mutant_killed': bool(no_lock and no_lock['violating_cases']),
               'all_mutants_killed': all(c['violating_cases'] for c in summaries if c['kind'] == 'mutant'),
               'coverage_valid': all(not c['coverage_errors'] for c in summaries),
               'phase4_external_writer': {'status': 'not_run', 'I4': 'not_applicable'},
               'c6c08f1_note': 'PR195 1e5b168 follows c6c08f13ad4e5fa1491e1d97e1cb73d2c9678022; compact code unchanged'}
    write_json(output / 'summary.json', summary)
    (output / 'REPORT.md').write_text(report_markdown(summary), encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('case_count', 'reference_no_violations', 'lock_mutant_killed', 'survivors', 'coverage_valid')}, indent=2))
    valid = summary['coverage_valid'] and all(c['compatible'] for c in checks)
    if reference:
        valid = valid and summary['reference_no_violations'] and (args.crash or summary['lock_mutant_killed'])
    if args.crash:
        summary['phases'] = [2]
        summary['scope'] = 'process os._exit(17) at operation boundaries, followed by compact and retry; no power-loss model'
        write_json(output / 'summary.json', summary)
    return 0 if valid else 2


if __name__ == '__main__':
    raise SystemExit(main())
