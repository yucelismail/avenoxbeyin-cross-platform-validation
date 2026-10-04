#!/usr/bin/env python3
"""Two-process invariant probe for the proposed #193 follow-up."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import tempfile

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
OLD = 'OLD_CARD_CONTENT_MUST_REMAIN_RECOVERABLE'
OLD_CARD = '## 2026-09-01 09:00 · eski · a\n' + OLD + '\n' + 'eski veri ' * 300 + '\n\n'
NEWEST = 'NEWEST_CARD_CONTENT'
ALLOWED = {'compacted', 'conflict', 'needs_rewrite', 'within_limit'}


def modules(repo, temp_root):
    tempfile.tempdir = str(temp_root)
    sys.path.insert(0, str(Path(repo) / 'template/.claude/scripts'))
    import beyin_v3_compact
    return beyin_v3_compact


def slow_worker(repo, vault, state, temp_root, ready, resume, out):
    compact = modules(repo, temp_root)
    original = compact._write
    paused = False

    def write(path, content):
        nonlocal paused
        if Path(path).parent.name == 'Arşiv' and not paused:
            paused = True
            ready.set()
            if not resume.wait(30):
                raise TimeoutError('slow process was not released')
        original(path, content)

    compact._write = write
    out.put(('slow', compact.compact(vault, state, now=NOW)))


def fast_worker(repo, vault, state, temp_root, done, out):
    compact = modules(repo, temp_root)
    try:
        out.put(('fast', compact.compact(vault, state, now=NOW)))
    finally:
        done.set()


def alias(path, link):
    try:
        link.symlink_to(path, target_is_directory=True)
        return link, True
    except OSError:
        return path, False


def scenario(repo, root, existing_archive, split_state, use_aliases):
    vault = root / 'vault'
    companion = vault / '🔮 850-Companion'
    companion.mkdir(parents=True)
    live = companion / 'Last-Session.md'
    archive = companion / 'Arşiv/Last-Session-2026-10.md'
    live.write_text('# Son oturum\n\n' + OLD_CARD
                    + '## 2026-09-02 09:00 · yeni · b\n' + NEWEST + '\n'
                    + 'yeni veri ' * 300 + '\n', encoding='utf-8')
    if existing_archive:
        archive.parent.mkdir()
        archive.write_text('# EXISTING_ARCHIVE_MARKER\n', encoding='utf-8')

    slow_state = root / 'state-slow'
    fast_state = root / ('state-fast' if split_state else 'state-slow')
    slow_tmp_real, fast_tmp_real = root / 'tmp-slow', root / 'tmp-fast'
    slow_tmp_real.mkdir()
    fast_tmp_real.mkdir()
    slow_tmp, slow_tmp_alias = alias(slow_tmp_real, root / 'tmp-slow-alias') if use_aliases else (slow_tmp_real, False)
    fast_vault, vault_alias = alias(vault, root / 'vault-alias') if use_aliases else (vault, False)

    sys.path.insert(0, str(repo / 'template/.claude/scripts'))
    from beyin_v3_companion import save_limits
    for state in {slow_state, fast_state}:
        save_limits(state, {'Last-Session.md': 3000, 'Threads.md': 8000})

    context = mp.get_context('spawn')
    ready, resume, done = context.Event(), context.Event(), context.Event()
    out = context.Queue()
    slow = context.Process(target=slow_worker,
                           args=(repo, vault, slow_state, slow_tmp, ready, resume, out))
    slow.start()
    if not ready.wait(25):
        slow.terminate()
        raise AssertionError('slow process did not reach archive write')
    fast = context.Process(target=fast_worker,
                           args=(repo, fast_vault, fast_state, fast_tmp_real, done, out))
    fast.start()
    finished_before_release = done.wait(3)  # Diagnostic only.
    resume.set()
    slow.join(30)
    fast.join(30)
    for process in (slow, fast):
        if process.is_alive():
            process.terminate()
            process.join()
    if (slow.exitcode, fast.exitcode) != (0, 0):
        raise AssertionError(f'child exit codes: {(slow.exitcode, fast.exitcode)}')
    results = dict(out.get(timeout=5) for _ in range(2))
    out.close()
    out.join_thread()
    live_bytes = live.read_bytes()
    archive_bytes = archive.read_bytes() if archive.exists() else b''
    # Path.write_text uses the host newline. Compare the exact bytes that were placed in
    # the fixture instead of treating Windows CRLF as data loss.
    expected_old_card = OLD_CARD.replace('\n', os.linesep).encode('utf-8')
    statuses = {actor: {'overall': result.get('status'),
                        'file': result.get('files', {}).get('Last-Session.md', {}).get('status')}
                for actor, result in results.items()}
    compacted = any('compacted' in values.values() for values in statuses.values())
    invariants = {
        'I1_full_old_card_preserved': expected_old_card in live_bytes or expected_old_card in archive_bytes,
        'I2_compacted_claim_has_archive': not compacted or expected_old_card in archive_bytes,
        'I3_progress': all(value['overall'] in ALLOWED and value['file'] in ALLOWED
                           for value in statuses.values()),
        'existing_archive_preserved': not existing_archive or b'EXISTING_ARCHIVE_MARKER' in archive_bytes,
        'newest_preserved': NEWEST.encode() in live_bytes or NEWEST.encode() in archive_bytes,
        'persistent_lock_exists': (companion / '.beyin-compact.lock').is_file(),
    }
    return {'existing_archive': existing_archive, 'split_state': split_state,
            'requested_alias_profile': use_aliases, 'vault_alias_supported': vault_alias,
            'tmp_symlink_supported': slow_tmp_alias,
            'fixture_newline': 'CRLF' if os.linesep == '\r\n' else 'LF',
            'fast_finished_before_release': finished_before_release,
            'statuses': statuses, 'invariants': invariants,
            'passed': all(invariants.values())}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: compact_probe.py /path/to/avenoxbeyin')
    repo = Path(sys.argv[1]).resolve()
    rows = []
    with tempfile.TemporaryDirectory(prefix='beyin-platform-probe-') as temporary:
        base = Path(temporary)
        for index, (existing, split, aliases) in enumerate([
                (False, False, False), (True, False, False),
                (False, True, True), (True, True, True)]):
            root = base / f'case-{index}'
            root.mkdir()
            rows.append(scenario(repo, root, existing, split, aliases))
    report = {'platform': sys.platform, 'python': sys.version, 'rows': rows,
              'passed': all(row['passed'] for row in rows)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    mp.freeze_support()
    raise SystemExit(main())
