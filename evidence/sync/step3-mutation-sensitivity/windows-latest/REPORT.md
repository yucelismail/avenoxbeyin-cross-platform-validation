## Multi-device sync probe results

main/pr210 are historical comparisons. The acceptance gate checks the patched fixed candidate; baseline failures remain in this report.

| Candidate | Case | Repeat | Failed checks | Coverage error |
| --- | --- | ---: | --- | --- |
| main | same_payload | 1 | none | none |
| main | same_payload | 2 | none | none |
| main | replacement | 1 | S3, S4 | none |
| main | replacement | 2 | S3, S4 | none |
| main | conflict_copy | 1 | S5 | none |
| main | conflict_copy | 2 | S5 | none |
| main | git_add_add | 1 | S3, S4 | none |
| main | git_add_add | 2 | S3, S4 | none |
| main | inplace_changed | 1 | S3, S4 | none |
| main | inplace_changed | 2 | S3, S4 | none |
| main | inplace_same | 1 | none | none |
| main | inplace_same | 2 | none | none |
| pr210 | same_payload | 1 | none | none |
| pr210 | same_payload | 2 | none | none |
| pr210 | replacement | 1 | S2, S4 | none |
| pr210 | replacement | 2 | S2, S4 | none |
| pr210 | conflict_copy | 1 | none | none |
| pr210 | conflict_copy | 2 | none | none |
| pr210 | git_add_add | 1 | S2, S4 | none |
| pr210 | git_add_add | 2 | S2, S4 | none |
| pr210 | inplace_changed | 1 | S3, S4 | none |
| pr210 | inplace_changed | 2 | S3, S4 | none |
| pr210 | inplace_same | 1 | none | none |
| pr210 | inplace_same | 2 | none | none |
| fixed | same_payload | 1 | none | none |
| fixed | same_payload | 2 | none | none |
| fixed | replacement | 1 | none | none |
| fixed | replacement | 2 | none | none |
| fixed | conflict_copy | 1 | none | none |
| fixed | conflict_copy | 2 | none | none |
| fixed | git_add_add | 1 | none | none |
| fixed | git_add_add | 2 | none | none |
| fixed | inplace_changed | 1 | none | none |
| fixed | inplace_changed | 2 | none | none |
| fixed | inplace_same | 1 | none | none |
| fixed | inplace_same | 2 | none | none |
| silent_receipt_update | same_payload | 1 | none | none |
| silent_receipt_update | same_payload | 2 | none | none |
| silent_receipt_update | replacement | 1 | S2, S4 | none |
| silent_receipt_update | replacement | 2 | S2, S4 | none |
| silent_receipt_update | conflict_copy | 1 | none | none |
| silent_receipt_update | conflict_copy | 2 | none | none |
| silent_receipt_update | git_add_add | 1 | S2, S4 | none |
| silent_receipt_update | git_add_add | 2 | S2, S4 | none |
| silent_receipt_update | inplace_changed | 1 | S2, S4 | none |
| silent_receipt_update | inplace_changed | 2 | S2, S4 | none |
| silent_receipt_update | inplace_same | 1 | none | none |
| silent_receipt_update | inplace_same | 2 | none | none |
| skip_receipt_rescan | same_payload | 1 | none | none |
| skip_receipt_rescan | same_payload | 2 | none | none |
| skip_receipt_rescan | replacement | 1 | S3, S4 | none |
| skip_receipt_rescan | replacement | 2 | S3, S4 | none |
| skip_receipt_rescan | conflict_copy | 1 | S5 | none |
| skip_receipt_rescan | conflict_copy | 2 | S5 | none |
| skip_receipt_rescan | git_add_add | 1 | S3, S4 | none |
| skip_receipt_rescan | git_add_add | 2 | S3, S4 | none |
| skip_receipt_rescan | inplace_changed | 1 | S3, S4 | none |
| skip_receipt_rescan | inplace_changed | 2 | S3, S4 | none |
| skip_receipt_rescan | inplace_same | 1 | none | none |
| skip_receipt_rescan | inplace_same | 2 | none | none |
| no_conflict_copy_filter | same_payload | 1 | none | none |
| no_conflict_copy_filter | same_payload | 2 | none | none |
| no_conflict_copy_filter | replacement | 1 | none | none |
| no_conflict_copy_filter | replacement | 2 | none | none |
| no_conflict_copy_filter | conflict_copy | 1 | S5 | none |
| no_conflict_copy_filter | conflict_copy | 2 | S5 | none |
| no_conflict_copy_filter | git_add_add | 1 | none | none |
| no_conflict_copy_filter | git_add_add | 2 | none | none |
| no_conflict_copy_filter | inplace_changed | 1 | none | none |
| no_conflict_copy_filter | inplace_changed | 2 | none | none |
| no_conflict_copy_filter | inplace_same | 1 | none | none |
| no_conflict_copy_filter | inplace_same | 2 | none | none |
| always_succeeded | same_payload | 1 | none | none |
| always_succeeded | same_payload | 2 | none | none |
| always_succeeded | replacement | 1 | S3, S4 | none |
| always_succeeded | replacement | 2 | S3, S4 | none |
| always_succeeded | conflict_copy | 1 | S5 | none |
| always_succeeded | conflict_copy | 2 | S5 | none |
| always_succeeded | git_add_add | 1 | S3, S4 | none |
| always_succeeded | git_add_add | 2 | S3, S4 | none |
| always_succeeded | inplace_changed | 1 | S3, S4 | none |
| always_succeeded | inplace_changed | 2 | S3, S4 | none |
| always_succeeded | inplace_same | 1 | none | none |
| always_succeeded | inplace_same | 2 | none | none |
| delete_quarantined_note_copy | same_payload | 1 | none | none |
| delete_quarantined_note_copy | same_payload | 2 | none | none |
| delete_quarantined_note_copy | replacement | 1 | none | none |
| delete_quarantined_note_copy | replacement | 2 | none | none |
| delete_quarantined_note_copy | conflict_copy | 1 | S5 | none |
| delete_quarantined_note_copy | conflict_copy | 2 | S5 | none |
| delete_quarantined_note_copy | git_add_add | 1 | none | none |
| delete_quarantined_note_copy | git_add_add | 2 | none | none |
| delete_quarantined_note_copy | inplace_changed | 1 | none | none |
| delete_quarantined_note_copy | inplace_changed | 2 | none | none |
| delete_quarantined_note_copy | inplace_same | 1 | none | none |
| delete_quarantined_note_copy | inplace_same | 2 | none | none |

S2: event content change visibility; S3: disk/SQLite agreement; S4: source-specific divergence warning; S5: conflict-copy quarantine.

Node runtime/runner notices are separate from these measured receipt contract failures.

## Negative-control sensitivity

| Mutant | Killed runs | Designated invariant caught twice |
| --- | ---: | --- |
| silent_receipt_update | 6 | True |
| skip_receipt_rescan | 8 | True |
| no_conflict_copy_filter | 2 | True |
| always_succeeded | 8 | True |
| delete_quarantined_note_copy | 2 | True |
