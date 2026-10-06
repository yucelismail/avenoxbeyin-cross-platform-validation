"""Receipt identity contract on synthetic vaults; candidate selected by environment."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(os.environ['SYNC_CANDIDATE']) / 'template/.claude/scripts'))
import beyin_v3_sync as subject


class ReceiptContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.vault = Path(self.tmp.name) / 'Synthetic Çalışma'
        (self.vault / 'notes').mkdir(parents=True)
        for name in ('source', 'other'):
            (self.vault / 'notes' / (name + '.md')).write_text('Synthetic note\n', encoding='utf-8')
        self.engine = subject.SyncEngine(self.vault, Path(self.tmp.name) / 'state')
        result = self.engine.receipt('synthetic-event', 'Original summary', ['notes/source.md'], 'manual', session='original')
        self.source = result['source']
        self.path = self.vault / self.source
        self.original = self.path.read_bytes()
        self.metadata, self.body = subject.parse(self.original.decode())
        with self.engine.store._connect() as db:
            self.stored = db.execute('SELECT payload FROM receipts WHERE id=?', ('synthetic-event',)).fetchone()[0]
        # Force an uncached directory scan without timing or filesystem resolution assumptions.
        os.utime(self.path.parent, (1700000000, 1700000000))
        with self.engine.store._connect() as db:
            db.execute("DELETE FROM metadata WHERE key='receipt_scan_signature'")

    def replace(self, field, value):
        metadata = dict(self.metadata)
        body = self.body
        if field == 'summary':
            body = value + '\n'
        else:
            metadata[field] = value
        incoming = subject.render(metadata, body).encode()
        staging = self.path.with_suffix('.incoming')
        staging.write_bytes(incoming)
        os.replace(staging, self.path)
        os.utime(self.path.parent, (1700000001, 1700000001))
        return incoming

    def check_metadata(self, field, value):
        incoming = self.replace(field, value)
        for _ in range(2):
            result = self.engine.sync()
            self.assertEqual(result['status'], 'succeeded', result)
            self.assertFalse(any(w.get('source') == self.source for w in result['warnings']))
        self.check_preserved(incoming)

    def check_preserved(self, incoming):
        self.assertEqual(self.path.read_bytes(), incoming)
        with self.engine.store._connect() as db:
            self.assertEqual(db.execute('SELECT payload FROM receipts WHERE id=?', ('synthetic-event',)).fetchone()[0], self.stored)

    def check_conflict(self, field, value):
        incoming = self.replace(field, value)
        for _ in range(2):
            result = self.engine.sync()
            self.assertEqual(result['status'], 'degraded', result)
            warnings = [w for w in result['warnings'] if w.get('source') == self.source]
            self.assertEqual(len(warnings), 1, result)
            self.assertEqual(warnings[0]['event_id'], 'synthetic-event')
            self.assertEqual(warnings[0]['differing_fields'], [field])
            self.assertIn('resolution', warnings[0])
            self.assertIn('stored_semantic_sha256', warnings[0])
            self.assertIn('disk_semantic_sha256', warnings[0])
            self.check_preserved(incoming)

    def test_created_at_metadata(self):
        self.check_metadata('created_at', '2026-10-05T12:00:00+00:00')

    def test_session_metadata(self):
        self.check_metadata('session', 'other-session')

    def test_harness_metadata(self):
        self.check_metadata('harness', 'codex')

    def test_summary_conflict(self):
        self.check_conflict('summary', 'Different summary')

    def test_refs_conflict(self):
        self.check_conflict('refs', ['notes/other.md'])

    def test_same_content(self):
        self.check_metadata('session', 'original')

    def test_warm_sync_does_not_read_receipt(self):
        self.assertEqual(self.engine.sync()['status'], 'succeeded')
        with patch.object(self.engine, '_receipt_event', side_effect=AssertionError('warm receipt read')):
            self.assertEqual(self.engine.sync()['status'], 'succeeded')

    def test_inplace_edit_is_explicitly_out_of_scope(self):
        self.assertEqual(self.engine.sync()['status'], 'succeeded')
        stamp = self.path.parent.stat().st_mtime_ns
        self.path.write_bytes(subject.render(self.metadata, 'Inplace changed\n').encode())
        self.assertEqual(self.path.parent.stat().st_mtime_ns, stamp)
        self.assertEqual(self.engine.sync()['status'], 'succeeded')


if __name__ == '__main__':
    unittest.main()
