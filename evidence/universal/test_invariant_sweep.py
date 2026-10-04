"""Harness checks independent of candidate behavior and historical expectations."""
import tempfile
import types
import unittest
from pathlib import Path

import invariant_sweep as sweep


class InvariantOracleTest(unittest.TestCase):
    def payload(self, status='compacted', file_status='compacted'):
        return {'result': {'status': status, 'files': {'Last-Session.md': {'status': file_status}}},
                'exitcode': 0, 'timed_out': False}

    def test_false_success_is_caught_even_if_old_card_is_still_live(self):
        with tempfile.TemporaryDirectory() as directory:
            live, archive = Path(directory) / 'live', Path(directory) / 'archive'
            live.write_text(sweep.OLD, encoding='utf-8')
            observed = sweep.file_observation(live, archive)
            result, claims = sweep.oracle(observed, {'slow': self.payload()})
            self.assertTrue(result['I1'])
            self.assertFalse(result['I2'])
            self.assertTrue(result['I3'])
            self.assertEqual(claims, ['slow'])

    def test_file_success_under_needs_rewrite_is_checked(self):
        result, claims = sweep.oracle({'old_in_live': False, 'old_in_archive': False},
                                     {'slow': self.payload('needs_rewrite')})
        self.assertFalse(result['I1'])
        self.assertFalse(result['I2'])
        self.assertEqual(claims, ['slow'])

    def test_unexpected_status_error_and_timeout_fail_progress(self):
        observed = {'old_in_live': True, 'old_in_archive': True}
        for payload in [self.payload('needs_attention'),
                        dict(self.payload(), error='injected failure'),
                        dict(self.payload(), timed_out=True),
                        dict(self.payload(), exitcode=1)]:
            with self.subTest(payload=payload):
                self.assertFalse(sweep.oracle(observed, {'slow': payload})[0]['I3'])


class HookBoundaryTest(unittest.TestCase):
    def test_targets_alias_and_atomic_write_nesting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live, archive, other = (root / name for name in ('live', 'archive', 'other'))
            for file in (live, archive, other):
                file.write_bytes(b'initial')
            alias = root / 'alias'
            alias.symlink_to(live)

            def simulated_atomic(path, content):
                path.read_bytes()  # internal reads must not count as a new operation
                path.unlink()     # nor must atomic implementation details
                path.write_bytes(content.encode())

            compact = types.SimpleNamespace(_write=simulated_atomic)
            before = (Path.read_bytes, Path.unlink, compact._write)
            with sweep.Hooks(compact, live, archive, None, None, None, 1) as hooks:
                other.read_bytes()
                alias.read_bytes()
                compact._write(archive, 'new')
                archive.unlink()
            self.assertEqual([(e['kind'], e['target']) for e in hooks.trace],
                             [('read', 'live'), ('write', 'archive'), ('unlink', 'archive')])
            self.assertEqual((Path.read_bytes, Path.unlink, compact._write), before)

    def test_gate_is_before_the_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live, archive = root / 'live', root / 'archive'
            live.write_bytes(b'before')
            compact = types.SimpleNamespace(_write=lambda p, s: p.write_text(s))
            seen = []

            class Ready:
                def set(self):
                    seen.append('ready')

            class Resume:
                def wait(self, timeout):
                    live.write_bytes(b'changed while paused')
                    return True

            with sweep.Hooks(compact, live, archive, 1, Ready(), Resume(), 1) as hooks:
                value = live.read_bytes()
            self.assertEqual(value, b'changed while paused')
            self.assertTrue(hooks.paused)
            self.assertEqual(seen, ['ready'])


if __name__ == '__main__':
    unittest.main()
