# Взаимодействие команды

Synthetic roles: `dispatcher`, `researcher`, `writer`, `developer`, `reviewer`.

- dispatcher владеет governance и может читать все scopes;
- researcher предлагает public knowledge;
- writer читает approved team/public context, но не меняет canonical truth напрямую;
- developer владеет procedures;
- reviewer продвигает candidates после policy checks.

Agent capability card описывает `read_scopes`, `write_modes`, `write_sources` и `forbidden`. Неизвестный actor, source вне его capability, а также owner/scope, не совпадающие с source manifest, запрещаются до candidate. Promotion повторно проверяет эту границу, поэтому legacy или вручную подложенный candidate не обходит policy. Предложение не равно записи: даже допустимый agent сначала создаёт candidate. Ошибка маршрутизации видна через `writeback_target` до мутации.
