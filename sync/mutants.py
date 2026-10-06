"""Isolated source mutations; never modify the positive candidate or user vault."""
import hashlib
from pathlib import Path
import subprocess
from .run_probes import CASES

MUTANTS = {
    'silent_receipt_update': ('replacement', 'S2'),
    'skip_receipt_rescan': ('inplace_changed', 'S3'),
    'no_conflict_copy_filter': ('conflict_copy', 'S5'),
    'always_succeeded': ('replacement', 'S4'),
    'delete_quarantined_note_copy': ('conflict_copy', 'S5'),
}
SOURCE = Path('template/.claude/scripts/beyin_v3_sync.py')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('mutation anchor missing or ambiguous')
    return text.replace(old, new, 1)


def mutate(text, name):
    if name == 'silent_receipt_update':
        start = "                        warnings.append({'source': rel, 'event_id': event['event_id'],"
        end = "                                         'disk_payload_sha256': _hash(payload)})"
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('receipt warning mutation anchor mismatch')
        left, rest = text.split(start, 1)
        _, right = rest.split(end, 1)
        result = left + "                        db.execute('UPDATE receipts SET payload=? WHERE id=?', (payload, event['event_id']))" + right
    elif name == 'skip_receipt_rescan':
        result = replace_once(text, '    def _scan_receipts(self, db):\n',
                              '    def _scan_receipts(self, db):\n        return []  # NEGATIVE CONTROL\n')
    elif name == 'no_conflict_copy_filter':
        result = replace_once(text, '                if _is_sync_conflict_copy(name, file_set):',
                              '                if False:  # NEGATIVE CONTROL: note conflict-copy filter')
    elif name == 'always_succeeded':
        result = replace_once(text, "return {'status': 'conflict' if conflicts else 'degraded' if warnings else 'succeeded', 'indexed':",
                              "return {'status': 'succeeded', 'indexed':")
    elif name == 'delete_quarantined_note_copy':
        result = replace_once(text, '                if _is_sync_conflict_copy(name, file_set):\n',
                              '                if _is_sync_conflict_copy(name, file_set):\n                    self._path(relative).unlink()  # NEGATIVE CONTROL\n')
    else:
        raise ValueError('unknown mutant')
    compile(result, '<mutant>', 'exec')
    return result


def create(fixed, destination):
    original = (fixed / SOURCE).read_text(encoding='utf-8')
    candidates, manifest = {}, {}
    for name in MUTANTS:
        target = destination / name
        subprocess.run(['git', 'clone', '--no-hardlinks', str(fixed), str(target)],
                       check=True, capture_output=True, text=True, timeout=60)
        changed = mutate(original, name)
        (target / SOURCE).write_text(changed, encoding='utf-8', newline='')
        candidates[name] = target
        manifest[name] = {'source_sha256': hashlib.sha256(changed.encode()).hexdigest(),
                          'designated_case': MUTANTS[name][0], 'designated_invariant': MUTANTS[name][1]}
    return candidates, manifest


def evaluate(rows):
    report = {}
    for name, (case, invariant) in MUTANTS.items():
        observed = [r for r in rows if r['candidate'] == name]
        selected = [r for r in observed if r['case'] == case]
        killed = [r for r in observed if any(v is False for v in r.get('invariants', {}).values())]
        expected = {(c, repeat) for c in CASES for repeat in (1, 2)}
        complete = len(observed) == len(expected) and {(r['case'], r['repeat']) for r in observed} == expected
        report[name] = {'killed_runs': len(killed), 'designated_case': case,
                        'designated_invariant': invariant,
                        'designated_kill_verified': complete and len(selected) == 2 and all(
                            r.get('coverage_error') is None and r.get('exit_code') == 1 and
                            r.get('invariants', {}).get(invariant) is False for r in selected)}
    return report
