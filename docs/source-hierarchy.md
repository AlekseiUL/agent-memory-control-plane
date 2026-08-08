# Иерархия источников

Priority задаётся policy-as-code:

1. `governance` — source of truth, priority 100.
2. `source-card` — capability/domain boundary, priority 90.
3. `procedure-library` — проверенные процедуры, priority 70.
4. `public-knowledge` — публичная canonical knowledge, priority 60.
5. `profile-memory` — стабильные предпочтения и факты, priority 40.

Нижний источник не может заменить активную запись верхнего источника. Такое предложение создаёт conflict receipt. Равный или более высокий источник может создать новую active record; прежняя получает `superseded` и удаляется только из rebuildable FTS projection, но сохраняется в canonical history.
