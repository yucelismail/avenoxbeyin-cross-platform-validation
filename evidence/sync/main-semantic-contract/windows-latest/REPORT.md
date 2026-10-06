# Main semantic receipt validation

Result: **passed**

Pinned base: `9b9aa95848b7dbee6ba13415c3615671d4445862`

| Candidate | Repeat | Tests | Assertion failures | Setup errors |
| --- | ---: | ---: | --- | --- |
| main | 1 | 8 | test_refs_conflict, test_summary_conflict | none |
| main | 2 | 8 | test_refs_conflict, test_summary_conflict | none |
| fixed | 1 | 8 | none | none |
| fixed | 2 | 8 | none | none |
| full_payload_compare | 1 | 8 | test_created_at_metadata, test_harness_metadata, test_refs_conflict, test_session_metadata, test_summary_conflict | none |
| full_payload_compare | 2 | 8 | test_created_at_metadata, test_harness_metadata, test_refs_conflict, test_session_metadata, test_summary_conflict | none |
| skip_existing_receipts | 1 | 8 | test_refs_conflict, test_summary_conflict | none |
| skip_existing_receipts | 2 | 8 | test_refs_conflict, test_summary_conflict | none |
| always_succeeded | 1 | 8 | test_refs_conflict, test_summary_conflict | none |
| always_succeeded | 2 | 8 | test_refs_conflict, test_summary_conflict | none |

Directory mtime cache is preserved. In-place changes without directory changes are explicitly outside this candidate. Metadata differences preserve indexed metadata and are not event collisions. Full payload hashes are not semantic identity. No automatic conflict repair or distributed locking is implemented.
