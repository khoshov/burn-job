# 001 — Нормальный парсер `.jfr` вместо скрейпинга текста `jfr print`

## Problem

`convert_jfr_if_needed()` в `skill/scripts/jfr_to_graph.py:21-79` конвертирует `.jfr` в
`.collapsed` двумя ненадёжными способами:
1. Ищет `one.profiler.Converter` внутри `target/bad-hibernate-demo-0.0.1-SNAPSHOT.jar` —
   то есть требует, чтобы именно этот Maven-проект был заранее собран (`jfr_to_graph.py:34-43`).
2. Фолбэк — запускает `jfr print --events jdk.ExecutionSample,ExecutionSample` и построчно
   скрейпит текстовый вывод по подстрокам `"method = "`/`"frame = "` (`jfr_to_graph.py:56-75`).
   Это не парсинг, а угадывание формата текстового вывода конкретной версии JDK; при этом
   безвозвратно теряются все остальные типы событий JFR (аллокации, retained-объекты, локи) —
   в `.collapsed` формате физически нет места ни для чего, кроме одного трейса CPU-сэмплов.

Мы эмпирически подтвердили (см. отчёт в этой сессии), что даже CPU-путь (async-profiler → `.collapsed`)
работает, но `.jfr` → `.collapsed` путь остаётся хрупким и однобоким.

## Goal

Заменить оба способа единым надёжным парсером `.jfr`, который за один проход извлекает
несколько типов событий (не только CPU) через официальный JDK API `jdk.jfr.consumer.RecordingFile`,
и отдаёт структурированные данные напрямую в Python (без промежуточного текстового формата).

## Non-goals

- Не переделывать схему KùzuDB — это спека [002](002-graph-schema-extension.md).
- Не трогать путь `.collapsed`-инжеста для async-profiler (он уже работает и подтверждён тестом).
- Не добавлять поддержку событий, для которых пока нет потребителя (см. только события ниже).

## Approach

1. Небольшая Java-утилита `skill/tools/JfrDump.java` (компилируется на лету через `javac`,
   без внешних зависимостей, только `jdk.jfr.consumer.RecordingFile` из самого JDK):
   - принимает путь к `.jfr`;
   - читает события `jdk.ExecutionSample`, `jdk.NativeMethodSample`, `jdk.ObjectAllocationSample`,
     `jdk.OldObjectSample`, `jdk.JavaMonitorEnter`, `jdk.ThreadPark`;
   - для каждого события восстанавливает стек (`event.getStackTrace().getFrames()`) и печатает
     единую построчную JSON-структуру в stdout (по одной строке на событие — ndjson), с полями:
     `eventType`, `stack` (список `pkg.Class.method`), и специфичные для типа события поля
     (`allocationSize`/`weight` для аллокаций, `duration` для монитор/park-событий, `object.className`
     для `OldObjectSample`).
2. В `jfr_to_graph.py` заменить `convert_jfr_if_needed()` + `parse_collapsed_stack()` для `.jfr`-входа
   на вызов `JfrDump` через `subprocess` и построчный разбор ndjson — без промежуточного `.collapsed`
   файла и без зависимости от `target/*.jar` или системной утилиты `jfr`.
3. Путь `.collapsed`-входа (уже существующий, для async-profiler) оставить как есть — это
   отдельный формат, не требующий изменений.
4. Компиляцию `JfrDump.java` делать лениво и кэшировать `.class` рядом с `.java`
   (аналогично тому, как сейчас ищется `target/*.jar`, но без внешней сборки всего проекта).

## Files touched

- `skill/tools/JfrDump.java` (новый файл)
- `skill/scripts/jfr_to_graph.py` (изменить `convert_jfr_if_needed`, добавить ndjson-парсинг,
  убрать зависимость от `jfr` CLI и `target/*.jar`)

## Acceptance criteria

- [ ] `JfrDump.java` компилируется чистым `javac` без внешних библиотек на JDK 17+.
- [ ] На `.jfr`-файле, записанном через `-XX:StartFlightRecording=settings=profile`, скрипт
      извлекает события всех 6 перечисленных типов (проверяется по факту непустых списков на
      тестовом профиле, который содержит хотя бы аллокации и один CPU-сэмпл).
- [ ] Старый `--dry-run` режим `jfr_to_graph.py` по-прежнему печатает top-methods/top-edges,
      теперь на основе данных из `JfrDump`, а не текстового скрейпинга.
- [ ] Путь без `kuzu`/`target/*.jar`/системной `jfr` CLI работает end-to-end (единственная
      внешняя зависимость — `java`/`javac`, которые уже требуются проекту).
- [ ] Ручной regression: старый `.collapsed`-путь (async-profiler) не сломан — тот же тест,
      что использовался в этой сессии, проходит без изменений.

## Dependencies

Нет (это первая, независимая спека). [002](002-graph-schema-extension.md) зависит от неё.
