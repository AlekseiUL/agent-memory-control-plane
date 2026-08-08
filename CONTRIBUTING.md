# Contributor guide

1. Используйте Python 3.11+ и только synthetic fixtures.
2. Начните с failing test для нового policy behavior.
3. Сохраняйте dry-run default, scope deny-by-default и provenance fields.
4. Не добавляйте cloud/connector auto-install, credential examples или абсолютные локальные пути.
5. Package resources загружайте через `importlib.resources`.
6. Запустите unit tests, scenarios, public/secret scan и clean normal-install smoke.
7. Изменения precedence, privacy или mutation boundary требуют отдельного reviewer.

Commit не должен включать generated database, virtual environment или cache.
