# Main-only semantic receipt candidate

Base: `9b9aa95848b7dbee6ba13415c3615671d4445862`. This is the pinned historical main used in the prior investigation, not a claim about current upstream HEAD. The new candidate does not depend on #210 or change #198 locking.

Receipt identity matches submission and recovery: same event ID with different `summary` or ordered `refs` is a collision. Valid `created_at`, `session`, and `harness` differences alone are not collisions. Indexed payload remains authoritative in every case. Disk contents are preserved. Source immutability checks in `receipt()` remain unchanged: a metadata-only disk edit can still be rejected by that write API even though sync reports no semantic collision.

Directory signature optimization remains. Changed-directory scans inspect known receipt contents; unchanged-directory warm scans return at the existing stat shortcut. This candidate intentionally does not detect in-place edits with unchanged directory mtime. Changed-directory scan cost is O(receipt bytes); unresolved warnings keep scans active. Performance benchmarking and metadata index alternatives are separate work.

Warnings provide source, event ID, differing fields, stored/disk semantic values and hashes, and guidance to back up both versions then restore indexed summary/refs or submit a distinct event ID. There is no repair command and no automatic deletion. Restoring semantic fields clears a sync collision, but source byte identity may still require restoring the original file for `receipt()` writes.

## Acceptance

Run `python run_semantic_validation.py` or supply `--main-checkout /path/to/pinned-main` for offline validation. Every candidate executes eight tests twice:

- Three metadata positive controls; same-content positive control.
- Separate summary and refs conflict tests, each checking two sync calls, warning contents and preservation of disk/SQLite.
- Warm-scan optimization check.
- Explicit in-place-edit limitation check.

Fixed candidate must pass all tests and the existing 42 product sync tests. Historical main must fail exactly summary/refs conflict tests. Full-payload comparison mutant must fail all three metadata controls. Skip-known and always-success mutants must fail both semantic conflict tests. Setup errors never count as kills. Mutant compile/anchor errors fail setup.

The existing #210-based harness and evidence remain historical material; this new workflow is an independent acceptance gate. GitHub Actions runs Ubuntu, macOS and Windows with synthetic local fixtures, not cloud replication or physically distributed devices.
