# Step 2 — receipt edits behind unchanged directory timestamps

[Platform run](https://github.com/yucelismail/avenoxbeyin-cross-platform-validation/actions/runs/37510084607). Test package: `4311377`. Product commits: first step `f9c22b4`, second step `2595cfa`. Exact patch/source hashes are in platform summaries and manifest.

The first-step candidate missed an in-place receipt edit in two local repeats: succeeded, stale SQLite, S3/S4 violations. Raw before-results are in step1-negative-reference.

The second step removes the directory-only receipt scan shortcut. Existing legacy receipt_scan_signature values cannot suppress content inspection. Every sync now reads receipts. Both same-content and changed-content in-place writes verify unchanged directory mtime; identical content remains succeeded, changed payload remains visibly degraded without overwriting either version.

| Platform | Fixed probes | Sync tests | Coverage errors |
| --- | ---: | ---: | ---: |
| Ubuntu | 12/12 | 49/49 | 0 |
| macOS arm64 | 12/12 | 49/49 | 0 |
| Windows Server | 12/12 | 49/49 | 0 |

Each platform also runs 24 historical comparisons (main/PR #210) with their expected measured failures. This is not a claim of baseline product correctness. Full warm-content inspection costs O(total receipt bytes) per sync; performance is not benchmarked here. Optimize later without weakening this acceptance gate.

This evidence does not cover full S1 preservation, cloud transport, CRLF, crash/retry or dedicated mutation sweeps. No user vault or PR #198 change. Next stage: negative mutants for visibility, scanning and quarantine.
