# Границы сравнения

AMCP дополняет, а не заменяет vector database, conversation history или task tracker.

- Vector database отвечает на similarity; AMCP — на governance, precedence и scope.
- Conversation history полезна как secondary recall, но не является canonical source и не индексируется автоматически.
- Task tracker хранит runtime state; он не durable memory.
- Knowledge graph может быть optional projection, но не нужен baseline.
- MCP — transport adapter, а не источник прав.

Base retrieval lexical и детерминированный. Embeddings могут появиться как optional read-only projection при сохранении тех же policy gates и receipts.
