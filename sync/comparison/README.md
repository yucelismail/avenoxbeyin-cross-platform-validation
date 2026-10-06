# Receipt status policy comparison

Pinned main `9b9aa95848b7dbee6ba13415c3615671d4445862`; peer `13ea7258a602009380c20cc2e591a51e65641617`; ours is main plus the existing SHA-verified semantic receipt patch.

`python run_receipt_comparison.py` runs:

- 17 shared tests twice for main, ours, peer and three mutants.
- Original 8-test strict warning-schema suite for ours and peer, reported separately.
- Full upstream V3 unittest discovery and frozen retrieval gates for both positive candidates.

Three shared tests observe status effects on unrelated receipt writing, task updates and hook acknowledgement. They assert preservation of the original divergent receipt but do not declare blocking or permitting unrelated work the preferred product policy. Other shared tests check visibility, metadata distinction, repeated sync, restoration, ordered refs, combined changes, invalid metadata and the existing in-place/cache limitation.

Shared conflict checks accept either source-specific `warnings/degraded` or `conflicts/conflict`; missing our warning fields or returning conflict instead of degraded is not a common-contract failure. Existing strict-suite differences are classification/schema mismatches, not automatic findings against the peer.

Mutants are controlled variations of our production source and must fail designated shared scenarios twice; setup errors never count as kills. They do not prove sensitivity to every hypothetical regression in the peer.

The workflow runs Ubuntu, macOS and Windows on Python 3.13. Test code and artifacts live in this validation repository only. No product branch, PR or review comment is published by this workflow.
