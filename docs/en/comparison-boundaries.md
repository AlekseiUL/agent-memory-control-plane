# Comparison boundaries

Agent Memory Control Plane complements rather than replaces vector databases, conversation history, or task trackers.

- A vector database answers similarity questions; AMCP answers governance, precedence, and scope questions.
- Conversation history is useful secondary recall, but it is not a canonical source and is not indexed automatically.
- A task tracker stores runtime state; it is not durable memory.
- A knowledge graph may be an optional projection, but the baseline does not require one.
- MCP is a transport adapter, not a source of authority.

Baseline retrieval is lexical and deterministic. Embeddings can be added later as an optional read-only projection while preserving the same policy gates and receipts.

This project also does not replace backups, monitoring, recovery testing, or human review. It makes those boundaries visible instead of claiming that agents can never forget.
