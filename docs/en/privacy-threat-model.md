# Privacy and threat model

## Fail-closed defaults

- local-only SQLite baseline;
- no cloud calls;
- direct LLM writes disabled;
- unknown scopes denied;
- unknown actors and out-of-capability sources denied;
- owner and scope must match the source manifest;
- public readers can access only `public` records;
- session transcripts and runtime evidence are non-memory;
- credential-like assignments and private-key headers are rejected before candidate creation;
- automatic merge and delete are disabled.

## Threats and controls

| Threat | Control |
|---|---|
| Scope confusion | Actor-role access allow-list |
| Capability/source bypass | Deny-by-default actor registry and exact source/owner/scope checks at proposal and promotion |
| Lower-source poisoning | Deterministic precedence gate |
| Lost provenance | Required owner, source, confidence, and timestamp |
| Unexplained retrieval | Retrieval receipt and `explain` |
| Hidden mutation | Dry-run default and explicit `--apply` |
| History deletion | Supersession without canonical delete |
| Credential-like leakage | Pre-ingest classifier and release scan |
| Package-resource drift | `doctor`, resource tests, and clean-install smoke |

The MCP adapter does not expand rights. Every request uses the same `ControlPlane` policy boundary.

## Public-release boundary

Examples, tests, roles, and traces are synthetic. Public attribution links may be listed deliberately, but private email addresses, chat IDs, local paths, production commands, raw sessions, owner context, and non-generic commit identities fail the release scan.
