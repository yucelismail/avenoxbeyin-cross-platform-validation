# Multi-device sync phase 1 — platform evidence

Test code commit: `847d0a5`. [Actions run](https://github.com/yucelismail/avenoxbeyin-cross-platform-validation/actions/runs/37506394351).

| Runner | Runs | Violating runs | Coverage errors |
| --- | ---: | ---: | ---: |
| Linux / Python 3.13.15 | 16 | 10 | 0 |
| macOS arm64 / Python 3.13.15 | 16 | 10 | 0 |
| Windows Server 2025 / Python 3.13.15 | 16 | 10 | 0 |

All platforms used the same probe SHA-256 and pinned main/PR #210 commits. Repeated invariant outcomes match. Identical-payload controls pass on both candidates. Main shows silent disk/SQLite divergence after replacement and resolved Git add/add, and fails conflict-copy quarantine. PR #210 repairs the DB but does not surface the changed event; proposed S2/S4 fail. PR #210 conflict-copy checks pass on all three platforms.

Workflow failure means measured contract violations, not setup failure. No product fix has been applied. The immutable-event visibility contract remains a proposed acceptance policy.

First run 37506236046 exposed a Windows probe path-separator comparison error (12 violating runs). That harness bug was corrected in 847d0a5; the final Windows result is 10, matching Linux/macOS. The earlier run is not final product evidence.

## Current stage

Source/commit inventory and independent small reproducer stage are established. The acceptance harness has a working core and real local Git transport integration with cross-platform execution. Full S1–S10 coverage, negative mutants, crash/retry and CRLF sweeps are not complete. An unchanged-directory-mtime receipt probe is next, followed by sensitivity controls and a narrow product fix. Doctor visibility remains a later separate contribution.

Each runner simulates two devices with independent vault/state directories on one machine. This is not physical multi-machine/cloud transport validation; Windows Server is not Windows 11 MSIX. No user vault is used.

Per-platform summary, JSONL and runner logs are in the subdirectories. manifest.json records original ZIP hashes.
