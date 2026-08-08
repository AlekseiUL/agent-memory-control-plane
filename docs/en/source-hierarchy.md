# Source hierarchy

Priority is defined in policy-as-code:

1. `governance` — canonical policy, priority 100.
2. `source-card` — capability and domain boundary, priority 90.
3. `procedure-library` — verified procedures, priority 70.
4. `public-knowledge` — canonical public knowledge, priority 60.
5. `profile-memory` — stable preferences and facts, priority 40.

A lower-priority source cannot replace an active higher-priority record, even when the content is identical. The proposal creates a conflict receipt; canonical provenance and visibility stay unchanged.

An equal- or higher-priority accepted record may supersede the current record. The old record is removed from the rebuildable FTS projection but retained in canonical history with an explicit supersession link.
