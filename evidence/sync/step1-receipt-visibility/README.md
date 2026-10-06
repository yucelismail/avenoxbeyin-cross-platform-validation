# Step 1: receipt collision visibility candidate

[Test package commit 415f8bb](https://github.com/yucelismail/avenoxbeyin-cross-platform-validation/commit/415f8bb). [Three-platform run](https://github.com/yucelismail/avenoxbeyin-cross-platform-validation/actions/runs/37508519911).

Candidate base: PR #210 `bf7f993ffc90085cd5c430098e537bab72ddf8f6`. Product change local commit: `f9c22b4`; distributable patch: `sync/receipt-visibility.patch`. Patch SHA-256: `945df08760eba854f0b5118b88085131db93d7a226cf9433d0a191a3b14aa4ce`.

| Platform | Fixed probe runs | Fixed violations | Sync unit tests | Coverage errors |
| --- | ---: | ---: | ---: | ---: |
| Ubuntu | 8 | 0 | 48 passed | 0 |
| macOS arm64 | 8 | 0 | 48 passed | 0 |
| Windows Server | 8 | 0 | 48 passed | 0 |

Every platform also executes 16 historical main/PR #210 comparisons; ten of those still violate the proposed contract. They remain unchanged and visible in the raw evidence. Workflow success now means the patched candidate passes; it does not mean the historical baselines pass.

The product change removes silent same-event UPDATE. It preserves the disk source and existing SQLite payload, reports source/event identity and two payload hashes, and returns degraded until the divergence is resolved. Retry preserves the same unresolved warning and projection state. The prior clean-reconciliation unit test is deliberately changed to the proposed conservative collision policy; that is a product contract change, not maintainer approval.

Limitations: source-authoritative automatic cache repair is paused when payloads disagree. Derived views retain the existing SQLite version while degraded. No explicit acknowledgment/repair command is added. History is not protected against deleting/resetting local SQLite. Directory-mtime-invisible changes, crash/retry and CRLF are next steps. No claim of all S1–S10 passing, actual cloud transport, or Windows 11 MSIX validation. User vault and PR #198 are unchanged; the candidate is not installed or merged upstream.

Per-platform JSONL, summary, unit test logs, and report are attached in this directory. Original ZIP hashes are in manifest.json.
