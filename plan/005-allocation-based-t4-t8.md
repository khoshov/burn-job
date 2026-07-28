# 005 — T4/T8 по реальным байтам аллокаций вместо числа вызовов

## Problem

`t4_data_layout.py:24-49` (`BOXED_WRAPPER_OVERHEAD`) и `t8_memory_bloat.py:23-43`
(`IN_MEMORY_FILTERING`)/`46-66` (`EXCESSIVE_STRING_ALLOCATIONS`) судят о "перерасходе памяти"
по **числу вызовов** `Integer.valueOf`/`ArrayList.grow`/`StringBuilder.append`/`Stream.filter`
в CPU-графе. Это прокси через время, а не через объём памяти — метод может вызываться часто и
дёшево (маленькие объекты) или редко и дорого (большие объекты), и текущие правила эту разницу
не видят. Мы также подтвердили в этой сессии, что `t8_memory_bloat.py` дублирует правило
string-concat из `t1_redundant_ops.py` дословно.

## Goal

T4 и T8 запрашивают реальные байты аллокаций из узлов `Allocation` (спека
[002](002-graph-schema-extension.md)) вместо CPU-sample-count прокси. T4 дополнительно получает
статический расчёт раскладки объекта (JOL-подход) без необходимости запуска.

## Non-goals

- Не трогать T1 (у него остаётся своя версия string-concat правила — дедупликация с T8
  выполняется отдельно в [010](010-rule-config-externalization.md)).
- Не добавлять новые типы событий JFR — они уже добавлены в [001](001-native-jfr-parser.md)/[002](002-graph-schema-extension.md).

## Approach

1. **T4** (`t4_data_layout.py`):
   - новое правило `BOXED_WRAPPER_OVERHEAD` (замена текущего): `MATCH (a:Allocation)-[:ALLOCATED_BY]->(m:Method) WHERE a.className CONTAINS 'Integer'/'Long' RETURN m, sum(a.bytes) AS totalBytes` —
     порог теперь в байтах (`totalBytes > 10_000`, конкретное число — предмет тюнинга при
     первом реальном прогоне), а не в количестве вызовов.
   - новая функция `compute_static_object_layout(class_file_path) -> dict` — читает объявленные
     поля класса (через `javap -p -v` или ASM: имя, тип, порядок) и по правилам выравнивания
     HotSpot (8-байтовый header + выравнивание полей по 4/8 байт) считает реальный размер
     инстанса и "потерянный" padding, если поля переставить по убыванию размера. Используется
     как отдельное правило `WASTED_FIELD_PADDING`, работающее без единого запуска приложения —
     на списке классов из `src/main/java/**`.
2. **T8** (`t8_memory_bloat.py`):
   - `IN_MEMORY_FILTERING`/`EXCESSIVE_STRING_ALLOCATIONS` получают порог по `sum(Allocation.bytes)`
     на метод вместо `r.count` на ребре CALLS.
   - Severity пересчитывается по объёму (`HIGH` если суммарные байты на прогон превышают
     процент от общего аллоцированного объёма профиля, а не абсолютное число).

## Files touched

- `skill/scripts/analyzers/t4_data_layout.py`
- `skill/scripts/analyzers/t8_memory_bloat.py`
- `skill/scripts/object_layout.py` (новый файл: `compute_static_object_layout`)

## Acceptance criteria

- [ ] На тестовом `.jfr` с аллокациями T4/T8 выдают находки с полем `sample_count`, замененным
      на реальные байты (проверяется, что число соответствует `Allocation.bytes`, а не count ребра).
- [ ] `compute_static_object_layout` на классе с полями в "плохом" порядке (например `boolean`,
      `long`, `boolean`) вычисляет padding больше нуля и предлагает порядок с меньшим padding.
- [ ] На классе с уже оптимальным порядком полей `WASTED_FIELD_PADDING` не срабатывает
      (не даёт находку с нулевой экономией) — это прямая защита от той же ошибки, которую
      правило Раздела 7 (ND-1) сейчас ловит постфактум через текстовый матчинг.
- [ ] Regression: на нашем тестовом Java-приложении из этой сессии (StringBuilder/Stream-код)
      T8 больше не показывает `sample_count` в терминах CPU-сэмплов там, где есть данные аллокаций.

## Dependencies

[001](001-native-jfr-parser.md), [002](002-graph-schema-extension.md) — нужны реальные данные аллокаций.
