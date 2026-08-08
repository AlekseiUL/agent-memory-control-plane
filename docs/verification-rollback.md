# Verification и rollback

## Проверка

```bash
python -m compileall -q src tests examples scripts
python -m unittest discover -s tests -v
python examples/run_scenarios.py
python scripts/public_scan.py --history
```

Release gate дополнительно создаёт fresh clone и normal venv install, запускает все CLI commands, MCP tool listing, schemas/policies parse check, docs link check и demo.

## Rollback

Репозиторий изолирован. Rollback изменения — `git revert <commit>` после review. База пользователя не удаляется автоматически. Для восстановления projection создаётся новая БД через `init` и повторно продвигаются canonical inputs; production migration в MVP отсутствует. Удаление каталога или пользовательских данных не является автоматическим действием.
