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
| pr210 | same_payload | 1 | none | none |
| pr210 | same_payload | 2 | none | none |
| pr210 | replacement | 1 | S2, S4 | none |
| pr210 | replacement | 2 | S2, S4 | none |
| pr210 | conflict_copy | 1 | none | none |
| pr210 | conflict_copy | 2 | none | none |
| pr210 | git_add_add | 1 | S2, S4 | none |
| pr210 | git_add_add | 2 | S2, S4 | none |
| fixed | same_payload | 1 | none | none |
| fixed | same_payload | 2 | none | none |
| fixed | replacement | 1 | none | none |
| fixed | replacement | 2 | none | none |
| fixed | conflict_copy | 1 | none | none |
| fixed | conflict_copy | 2 | none | none |
| fixed | git_add_add | 1 | none | none |
| fixed | git_add_add | 2 | none | none |

S2: event content change visibility; S3: disk/SQLite agreement; S4: source-specific divergence warning; S5: conflict-copy quarantine.

Node runtime/runner notices are separate from these measured receipt contract failures.
