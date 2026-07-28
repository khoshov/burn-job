# 002 — Расширение схемы KùzuDB под аллокации, retained-объекты и блокировки

## Problem

Текущая схема в `init_kuzu_schema()` (`skill/scripts/jfr_to_graph.py:161-174`) знает только
`Method`/`CALLS` (CPU-граф вызовов). Поле `runId` уже есть на `CALLS`, но нигде не используется
для межпрогонного сравнения. Данные аллокаций/retained-объектов/блокировок, которые появятся
после [001](001-native-jfr-parser.md), негде хранить — их сейчас некуда положить в граф.

## Goal

Добавить в схему три новых типа узлов и связать их с `Method`, чтобы анализаторы T4/T7/T8/T9
могли запрашивать реальные данные вместо CPU-сэмплов как прокси.

## Non-goals

- Не переписывать сами анализаторы (T4/T7/T8/T9) — это спеки [005](005-allocation-based-t4-t8.md),
  [006](006-leak-detection-t7.md), [007](007-lock-contention-t9-and-regex-fix.md).
- Не добавлять сравнение между прогонами как отдельную фичу — это [011](011-relative-thresholds-and-multirun-diff.md).

## Approach

Новые таблицы (Cypher DDL, добавить в `init_kuzu_schema()`):

```cypher
CREATE NODE TABLE IF NOT EXISTS Allocation(
    id STRING, className STRING, bytes INT64, count INT64, runId STRING, PRIMARY KEY (id)
)
CREATE NODE TABLE IF NOT EXISTS RetainedObject(
    id STRING, className STRING, ageMs INT64, allocationStack STRING, runId STRING, PRIMARY KEY (id)
)
CREATE NODE TABLE IF NOT EXISTS MonitorBlock(
    id STRING, className STRING, durationMs INT64, runId STRING, PRIMARY KEY (id)
)
CREATE REL TABLE IF NOT EXISTS ALLOCATED_BY(FROM Allocation TO Method)
CREATE REL TABLE IF NOT EXISTS RETAINED_BY(FROM RetainedObject TO Method)
CREATE REL TABLE IF NOT EXISTS BLOCKED_IN(FROM MonitorBlock TO Method)
```

`ALLOCATED_BY`/`RETAINED_BY`/`BLOCKED_IN` указывают на верхний фрейм стека события (метод,
в котором произошла аллокация/удержание/блокировка) — тот же `Method.id`, что уже используется
для `CALLS`, так что узлы переиспользуются, а не дублируются.

Функция `ingest_to_kuzu()` (`jfr_to_graph.py:177-215`) получает новую версию/параллельную функцию
`ingest_jfr_events_to_kuzu()`, которая принимает ndjson-события от [001](001-native-jfr-parser.md)
и для каждого типа события создаёт узел + ребро на верхний фрейм стека, попутно `MERGE`-я
`Method`-узлы для всех фреймов стека (как уже делает текущий код для CPU-графа).

## Files touched

- `skill/scripts/jfr_to_graph.py` (расширить `init_kuzu_schema`, добавить `ingest_jfr_events_to_kuzu`)

## Acceptance criteria

- [ ] Схема создаётся идемпотентно (`CREATE ... IF NOT EXISTS`), повторный запуск на той же БД
      не падает.
- [ ] После ингеста тестового `.jfr` с аллокациями `MATCH (a:Allocation) RETURN count(a)` больше 0.
- [ ] Каждый `Allocation`/`RetainedObject`/`MonitorBlock` имеет `runId`, совпадающий с переданным
      `--run-id`.
- [ ] Старая схема (`Method`/`CALLS`/`Run`/`Test`) и её наполнение из `.collapsed`-пути не меняются.

## Dependencies

[001](001-native-jfr-parser.md) — нужен формат событий на выходе, под который проектируется схема.
