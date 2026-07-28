# 006 — T7 по retained-объектам и тренду между прогонами

## Problem

`t7_memory_leak.py:22-44` (`RETAINED_OBJECT_ACCUMULATION`) ищет метод по имени класса
(`OldObjectSample`/`WeakHashMap`/`ThreadLocal`/`Static`) с `sampleCount > 20` — это подстрока
в имени, а не признак реальной утечки. `t7_memory_leak.py:46-69`
(`UNBOUNDED_CACHE_OR_COLLECTION_GROWTH`) смотрит на число вызовов `put`/`add` в одном прогоне —
рост числа вызовов не то же самое, что рост удерживаемой памяти: кэш с активным вытеснением
(eviction) тоже может часто вызывать `put`.

Настоящая утечка — это рост retained-множества **во времени**, что принципиально не видно из
одного снимка графа.

## Goal

T7 использует реальные `RetainedObject`-узлы (спека [002](002-graph-schema-extension.md),
из события `jdk.OldObjectSample`) и запрос тренда по нескольким `runId` одного и того же метода.

## Non-goals

- Не реализовывать автоматический запуск нескольких профилирующих прогонов — предполагается,
  что вызывающий код (например нагрузочный тест) уже гоняет профиль несколько раз подряд с
  разными `run-id` и передаёт их все в одну БД (что уже поддерживает текущий `--run-id` аргумент
  `jfr_to_graph.py`).

## Approach

1. Заменить `RETAINED_OBJECT_ACCUMULATION` на запрос по реальным `RetainedObject`:
   ```cypher
   MATCH (r:RetainedObject)-[:RETAINED_BY]->(m:Method)
   RETURN m, r.className, count(r) AS retainedCount, avg(r.ageMs) AS avgAge
   ```
   Порог — по `retainedCount` и `avgAge` (объекты, живущие дольше N секунд между GC-циклами —
   уже сильный сигнал, доступный из самого события `OldObjectSample`, без сравнения прогонов).
2. Добавить `UNBOUNDED_GROWTH_TREND` — новый тип аномалии, требующий **минимум 2 разных runId**
   в базе: `MATCH (r:RetainedObject) WHERE r.runId IN [$run1, $run2] ... сравнить count(r) по runId`.
   Если retained-count монотонно растёт между последовательными `runId` для одного и того же
   метода — это и есть прямое доказательство утечки (не эвристика).
3. `UNBOUNDED_CACHE_OR_COLLECTION_GROWTH` (CALLS-based) остаётся как более дешёвый/ранний сигнал
   для случаев без запущенного `OldObjectSample`-профилирования, но severity понижается до `LOW`
   по умолчанию (это теперь явно вторичный, слабый сигнал, а не основной).

## Files touched

- `skill/scripts/analyzers/t7_memory_leak.py`

## Acceptance criteria

- [ ] На тестовом `.jfr` с событиями `OldObjectSample` (например, программа, накапливающая
      объекты в статическом списке без ограничения) T7 находит `RETAINED_OBJECT_ACCUMULATION`
      с реальным `avgAge`, отличным от нуля.
- [ ] На двух прогонах (`run1`, `run2`) с растущим retained-count для одного метода срабатывает
      `UNBOUNDED_GROWTH_TREND`.
- [ ] На двух прогонах с одинаковым/убывающим retained-count (например, кэш с bounded eviction)
      `UNBOUNDED_GROWTH_TREND` не срабатывает — прямая проверка того, что ND-3 (bounded cache)
      теперь имеет реальное основание не сработать, а не только текстовый матчинг на "caffeine".
- [ ] `UNBOUNDED_CACHE_OR_COLLECTION_GROWTH` (старое правило) не удалён, но его severity ниже,
      чем у нового `UNBOUNDED_GROWTH_TREND`, когда оба сработали на одном методе.

## Dependencies

[001](001-native-jfr-parser.md), [002](002-graph-schema-extension.md).
