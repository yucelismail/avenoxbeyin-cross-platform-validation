# `companion-compact` data-loss fix evidence

This directory publishes the source-matched evidence for commit `65f74aa3f916718a1033ee336d000efb9193eb1c` on top of upstream `9b9aa95848b7dbee6ba13415c3615671d4445862`.

## Identity

- Candidate patch SHA-256: `462e4e4e3975275269031fc5f278c59e67f8483793928fa7993a12f2fdb65f99`
- Patched `beyin_v3_compact.py` SHA-256: `02dc9b8fb57c93dac289a814a81656d9465f42086a28eac2149ac56b82763c7b`
- Invariant harness SHA-256: `3737c45ee498906c869c4fe4ae54e93d7ee89b01a4ca6159e6212ae7bbe4115b`

The same patched source hash appears in the invariant manifests and the Linux, macOS, and Windows summaries.

## Results

| Gate | Environment | Result |
| --- | --- | --- |
| Operation-boundary invariant sweep | Linux 7.0, Python 3.12.3, `spawn` | Reference 112/112 passed; 0 coverage errors |
| No-lock negative control | Linux 7.0, Python 3.12.3, `spawn` | 16/112 cases failed; 16 I1 and 16 I2 violations |
| Crash and retry sweep | Linux 7.0, Python 3.12.3, `spawn` | 112/112 passed; 0 coverage errors |
| Platform probe and suites | Linux, Python 3.12.3 | Probe passed; companion, product, and stdlib suites passed |
| Platform probe and suites | macOS 15.8.1 arm64, Python 3.14.8 | Probe 4/4; companion 87/87; product 15/15; stdlib 4/4 |
| Platform probe and suites | Windows 11, Python 3.13.14 | Probe passed; companion 87 tests with 3 skips; product 15/15; stdlib 4/4 |

The Windows machine could not create symlinks under its account, so its alias profile reports `vault_alias_supported: false` and `tmp_symlink_supported: false`. Those profiles ran on macOS, where both report `true` and pass. Split-state, new archive, existing archive, progress, persistent lock, I1, and I2 checks passed on Windows.

## Universal harness

- [`universal/invariant_sweep.py`](universal/invariant_sweep.py): bounded single-pause operation sweep, invariant oracle, no-lock mutant, and crash/retry mode.
- [`universal/test_invariant_sweep.py`](universal/test_invariant_sweep.py): harness self-tests.
- [`universal/INVARIANT-SWEEP.md`](universal/INVARIANT-SWEEP.md): design, invariants, dimensions, and limits.
- [`universal/results/invariant/`](universal/results/invariant/): readable report, summary, trace, source manifest, mutant patch, and all 224 reference/control cases.
- [`universal/results/crash/`](universal/results/crash/): crash/retry report and all 112 cases.

Run against a checkout on the validated Linux/Python 3.12.3 profile:

```bash
python3 -B evidence/universal/invariant_sweep.py \
  --checkout /path/to/avenoxbeyin \
  --output /tmp/compact-invariant-result \
  --jobs 4
```

Crash and retry mode:

```bash
python3 -B evidence/universal/invariant_sweep.py \
  --checkout /path/to/avenoxbeyin \
  --output /tmp/compact-crash-result \
  --jobs 4 \
  --crash
```

Harness self-tests:

```bash
python3 -B -m unittest discover \
  -s evidence/universal -p 'test_invariant_sweep.py' -v
```

## Platform evidence

The `platform/` directories contain sanitized extracted text from the final ZIP artifacts. `manifest.json` records both the original archive hashes and every published file hash. Local usernames and temporary paths were replaced with `$HOME`, `$TMPDIR`, `$VALIDATION_REPO`, or `%USERPROFILE%`; test outcomes and source hashes were not changed.

## Scope

The invariant sweep is bounded to one controlled pause at each observed live/archive operation boundary. It is not exhaustive model checking. Crash mode uses `os._exit(17)` between operations and does not model power loss or disk durability. Advisory lock behavior on NFS/SMB and independently synchronized vault copies remains outside the guarantee.
