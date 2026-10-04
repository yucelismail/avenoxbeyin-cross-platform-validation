# Historical failure anchors

These source-pinned Linux/Python 3.12.3 runs establish the failure before evaluating the candidate. Every concurrent scenario uses two real `spawn` processes and a deterministic `multiprocessing.Event` schedule.

| Source | Controlled schedule | New archive | Existing archive |
| --- | --- | --- | --- |
| v3.7.1 `16af4bc` | Same state/TMPDIR; pause after archive write | old card lost | old card lost |
| #194 `3279bb2` | Same state, split TMPDIR; pause before archive write | old card lost | old card lost |
| #195 `1e5b168` | Same state, split TMPDIR | preserved | preserved |
| #195 `1e5b168` | Split state and TMPDIR; pause before archive write | old card lost | old card lost |

The merged `main@9b9aa95` compact source is byte-identical to #194 `3279bb2`, and the split-TMPDIR loss was also rerun directly on that merge before preparing the candidate.

Files:

- [`issue-193-v3.7.1.json`](issue-193-v3.7.1.json)
- [`pr-194-3279bb2.json`](pr-194-3279bb2.json)
- [`pr-195-1e5b168.json`](pr-195-1e5b168.json)

The files retain the full scenario results, fixture identity, source commit and source file hashes. Local checkout paths are replaced with `$SOURCE_CHECKOUT`.
