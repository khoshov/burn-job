# 007 — T9: реальные блокировки вместо имён + фикс ложных срабатываний на JIT

## Problem

Два независимых бага в `t9_cpu_hotspots.py`, оба подтверждены эмпирически в этой сессии:

1. `THREAD_LOCK_CONTENTION` (`t9_cpu_hotspots.py:22-43`) ищет `className CONTAINS 'Lock'` или
   `methodName CONTAINS 'park'/'synchronized'` в CPU-графе — это не измерение времени блокировки,
   а догадка по имени. Поток мог быть заблокирован 5 мс или 5 секунд — правило не различает.
2. `MICROBENCHMARK_REGEX_COMPILE` (`t9_cpu_hotspots.py:70-89`) матчит `methodName CONTAINS 'compile'`
   **без какого-либо порога** (в отличие от всех остальных правил в файле). На нашем тестовом
   Java-приложении, не содержащем ни одного вызова `Pattern.compile`, это правило сработало
   8 раз — на всех восьми матчах это оказались внутренние фреймы JIT-компилятора JVM
   (`CompileBroker::compile_method`, `JavaThread::thread_main_inner`), а не regex пользователя.

## Goal

`THREAD_LOCK_CONTENTION` использует реальные `MonitorBlock`-узлы (длительность блокировки в мс)
вместо угадывания по имени. `MICROBENCHMARK_REGEX_COMPILE` получает порог и защиту от матчинга
на нативные/JVM-фреймы.

## Non-goals

- Не переписывать `CPU_HOTSPOT_METHOD` (`t9_cpu_hotspots.py:45-67`) — этот запрос уже прямо
  измеряет то, что заявляет (CPU-сэмплы = CPU-нагрузка), проблем с ним не найдено.

## Approach

1. `THREAD_LOCK_CONTENTION` → новый запрос:
   ```cypher
   MATCH (b:MonitorBlock)-[:BLOCKED_IN]->(m:Method)
   RETURN m, sum(b.durationMs) AS totalBlockedMs, count(b) AS blockCount
   ```
   Порог по `totalBlockedMs` (например `> 100`), а не по наличию слова "Lock" в имени.
2. `MICROBENCHMARK_REGEX_COMPILE` — два независимых фикса:
   - добавить `AND r.count > 15` (как у аналогичного правила в `non_defects.py` ND-5, которое
     уже ожидает этот порог, но текущий Cypher-запрос его не применяет);
   - добавить условие `a.className STARTS WITH <project package prefix>` (то же самое, что уже
     использует `CPU_HOTSPOT_METHOD` двумя правилами выше в том же файле) — исключает нативные
     фреймы JVM (`Global.*`, `C2Compiler::*`, `CompileBroker::*`), у которых `className` не
     принадлежит анализируемому проекту.
   - `pkg`/`className`, приходящие из нативных JFR-фреймов (`Global.CompileBroker::...`), уже
     помечаются отдельным неймспейсом `Global.` в `extract_class_and_method()`
     (`jfr_to_graph.py:142-158`) — использовать этот признак как дополнительный явный фильтр
     `NOT a.pkg = ''` или `NOT a.className = 'Global'`.

## Files touched

- `skill/scripts/analyzers/t9_cpu_hotspots.py`

## Acceptance criteria

- [ ] На тестовом `.jfr` с реальным `synchronized`-блоком, вызывающим измеримую задержку,
      `THREAD_LOCK_CONTENTION` находит его с `totalBlockedMs`, соответствующим фактической
      задержке (в пределах погрешности профилирования).
- [ ] Regression на нашем тестовом Java-приложении из этой сессии (без единого `Pattern.compile`
      или пользовательского лока): `MICROBENCHMARK_REGEX_COMPILE` не срабатывает ни разу
      (было 8 срабатываний, все ложные — все на `Global.CompileBroker::*`/`JavaThread::*`).
- [ ] На приложении с реальным `Pattern.compile(...)` в горячем пути правило продолжает
      срабатывать (не стало слишком строгим).

## Dependencies

[001](001-native-jfr-parser.md), [002](002-graph-schema-extension.md) — для `MonitorBlock`.
Regex-фикс (вторая часть) зависимостей не имеет и может быть сделан отдельно и раньше.
