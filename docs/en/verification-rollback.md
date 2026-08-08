# Verification and rollback

## Verification

```bash
python -m compileall -q src tests examples scripts
python -m unittest discover -s tests -v
python examples/run_scenarios.py
python scripts/public_scan.py --history
```

The release gate additionally creates a fresh clone and normal virtual-environment install, exercises every CLI command, lists all MCP tools, parses schemas and policy resources, checks documentation links, and runs the synthetic scenarios.

A public release should also verify that all reachable commits use generic author/committer metadata and that no remote contains an unpublished private history.

## Rollback

The repository is isolated. Revert a published change with reviewed `git revert <commit>`. The application never deletes a user database automatically.

The FTS projection is rebuildable. The baseline can create a fresh database with `init` and re-promote canonical inputs. A production migration framework is outside this MVP and must be designed before using real persistent data.

Deleting the repository or user data is never an automatic rollback action.
