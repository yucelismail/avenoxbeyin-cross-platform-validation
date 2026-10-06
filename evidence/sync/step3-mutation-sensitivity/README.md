# Step 3 — negative-control sensitivity

[Test package b0d1438](https://github.com/yucelismail/avenoxbeyin-cross-platform-validation/commit/b0d1438). [Platform run](https://github.com/yucelismail/avenoxbeyin-cross-platform-validation/actions/runs/37510833282). No new product change in this step.

All three platforms: 96 probe runs (12 positive candidate + 24 historical comparison + 60 mutant), zero coverage errors. Fixed candidate passes 12/12 and 49 sync unit tests. Five mutants each fail their designated invariant in both repeats.

| Mutant | Target case | Target invariant | Violating runs per platform |
| --- | --- | --- | ---: |
| silent_receipt_update | replacement | S2 | 6 |
| skip_receipt_rescan | inplace_changed | S3 | 8 |
| no_conflict_copy_filter | conflict_copy | S5 | 2 |
| always_succeeded | replacement | S4 | 8 |
| delete_quarantined_note_copy | conflict_copy | S5 | 2 |

The candidate and oracle remain unchanged during mutation. Mutants modify isolated copies of the patched sync source. Exact source SHA-256, construction targets and raw observations are published per platform. Syntax errors, bad mutation anchors, timeout, incomplete matrices and coverage errors never count as kills. Gate requires the designated invariant, not merely a nonzero exit.

Conflict-copy mutations target note quarantine only; receipt-specific hash-name quarantine has an additional predicate and is not fully mutated by this step. skip_receipt_rescan disables the scanner completely (not a warm-cache-only mutant). Results prove sensitivity in this six-case sweep, not every possible corruption or interleaving.

Three GitHub runner platforms each simulate independent vault/state directories; this is not cloud transport or Windows 11 MSIX evidence. No user vault changes. Full S1 preservation, CRLF and crash/retry remain open. Next stage: line-ending contract probes, then controlled crash/retry.
