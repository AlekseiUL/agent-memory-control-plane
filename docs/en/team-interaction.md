# Team interaction

Synthetic roles: `dispatcher`, `researcher`, `writer`, `developer`, and `reviewer`.

- `dispatcher` owns governance and may read all scopes;
- `researcher` proposes public knowledge;
- `writer` reads approved team/public context but cannot change canonical truth directly;
- `developer` owns procedures;
- `reviewer` promotes candidates after policy checks.

An agent capability card declares `read_scopes`, `write_modes`, `write_sources`, and `forbidden`. Unknown actors, sources outside an actor's capability, and owner/scope values that do not match the source manifest are denied before candidate creation.

Promotion repeats the same boundary check, so a legacy or manually inserted candidate cannot bypass policy. A proposal is not a write to canonical truth. The writeback target is visible before mutation, making routing errors inspectable.
