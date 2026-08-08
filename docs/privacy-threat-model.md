# Privacy model и threat model

## Fail-closed defaults

- local-only SQLite;
- cloud calls отсутствуют;
- LLM write отключён;
- неизвестный scope запрещён;
- public reader видит только `public`;
- session transcript и runtime evidence относятся к non-memory;
- secret assignment и private-key headers блокируются до candidate;
- auto-merge и auto-delete отключены.

## Угрозы и меры

| Угроза | Мера |
|---|---|
| Scope confusion | allow-list доступа по actor role |
| Poisoning нижним источником | deterministic precedence gate |
| Потеря provenance | обязательные owner/source/confidence/timestamp |
| Необъяснимый retrieval | retrieval receipt и `explain` |
| Скрытая мутация | dry-run default и явный `--apply` |
| Удаление истории | supersession без delete |
| Утечка credential-like строки | pre-ingest classifier и release scan |
| Drift package resources | `doctor`, resource tests, clean install smoke |

MCP adapter не расширяет права: каждый вызов проходит тот же `ControlPlane`.
