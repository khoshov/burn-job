# 015 — findings.json: соответствие evidence-полей схеме SUBMISSION.md

## Problem
Текущий (незакоммиченный) генератор `export_report.py`, реализующий
[004](004-findings-json-generator.md), расходится со схемой `TASK/SUBMISSION.md` в нескольких
конкретных местах:
- `evidence.channel` захардкожен как `"Profiler-Sample-Count"` для каждой находки
  (`export_report.py:178`) — не входит в требуемый enum
  `{X-Sql-Count, X-Elapsed-Ms, jvm.memory.used, jvm.memory.usage.after.gc, JFR}`. 100% находок
  проваливают это обязательное для `hard` поле.
- `evidence.after` захардкожен как `null` (`export_report.py:180`) для каждой находки — при этом
  сама спека 004 обещала честное приближённое before/after из `sample_count`/`percentage`, а не
  пустое значение.
- `pdf_taxonomy` — всегда список из одного элемента (`export_report.py:173`,
  `"pdf_taxonomy": [taxonomy_id]`), хотя пример в самом `TASK/SUBMISSION.md:58` показывает
  мультикатегорийность (`["T6","T2"]`), и старый ручной `findings.json` её тоже использовал.
- `evidence.how` не содержит ни одной детали воспроизведения и прямо пишет, что это не
  измерение (`export_report.py:181-185`) — риск попасть под штраф "невоспроизводимые числа".

Всё остальное соответствует схеме: верхнеуровневые ключи, `family` (валидный enum через реальную
таблицу маппинга `TAXONOMY_TO_FAMILY`/`T5_TYPE_TO_FAMILY`), ключи `checked_but_not_an_issue`.

## Goal
Привести `evidence.channel`, `evidence.after`, `pdf_taxonomy` и `evidence.how` в соответствие со
схемой `TASK/SUBMISSION.md`, не выдумывая при этом реальных двухпрогонных измерений (это остаётся
задачей [011](011-relative-thresholds-and-multirun-diff.md)) — честно и явно промаркированное
приближение вместо противоречащих схеме заглушек.

## Non-goals
- Не менять сам формат/схему `findings.json` — она зафиксирована судейским скриптом (тот же
  non-goal, что и в [004](004-findings-json-generator.md)).
- Не реализовывать `compare_runs()`/различие между двумя `runId` — это полностью зона
  [011](011-relative-thresholds-and-multirun-diff.md); эта спека только чинит однопрогонный
  fallback так, чтобы он не был структурно/по смыслу неверным до готовности 011.
- Не подключать HTTP-уровневые каналы (`X-Sql-Count`, `X-Elapsed-Ms` как заголовки живого
  нагрузочного теста) — граф/JFR-анализ этого не видит; `evidence.how` ограничивается тем, что
  реально выводимо из графа (run_id, test_name, состав сэмплов), а не придумывает эндпоинт.
- Не менять таблицу `TAXONOMY_TO_FAMILY`/`T5_TYPE_TO_FAMILY` — она уже корректна.

## Approach
1. **`evidence.channel`**: заменить константу на функцию `_channel_for(family: str) -> str`,
   маппящую `family` на валидный enum:
   - `db` → `"X-Sql-Count"` (граф уже считает количество SQL/JDBC-вызовов — семантически
     эквивалентно счётчику SQL-запросов, даже не будучи HTTP-заголовком).
   - `cpu` → `"JFR"`.
   - `memory` → `"jvm.memory.used"`, кроме находок T7 (retained-object/leak) →
     `"jvm.memory.usage.after.gc"` (пост-GC память — точнее описывает утечку).
   - `algo`, `redundant` → `"X-Elapsed-Ms"` (единственный оставшийся enum-член, семантически
     ближе всего к "лишнее время выполнения из-за неэффективного алгоритма/кода").
   Задокументировать в коде каждую ветку комментарием со ссылкой на конкретный enum-пункт
   `TASK/SUBMISSION.md`.
2. **`evidence.after`**: заменить `None` на `0`, явно промаркированный в `how` как *прогнозируемый
   результат применения фикса* (не измеренный) — число вместо `null`, честно описанное. Как
   только [011](011-relative-thresholds-and-multirun-diff.md)'s `compare_runs()` доступен и в базе
   есть ≥2 `runId`, `after` должен браться из реального differential-сравнения вместо этой
   заглушки (эта интеграция — задача 011, здесь только контракт/fallback).
3. **`pdf_taxonomy`**: добавить таблицу `ANOMALY_TYPE_TO_TAXONOMY_CODES` (по образцу уже
   существующей `FIX_SUGGESTIONS`, keyed по `anomaly_type`), перечисляющую все применимые коды
   для типов, которые по своей природе покрывают несколько таксономий (например
   `N_PLUS_ONE_QUERIES` → `["T6", "T2"]`); типы без явной записи в таблице продолжают давать
   список из одного `taxonomy_id`, как сейчас.
4. **`evidence.how`**: переписать шаблон так, чтобы он включал то, что реально доступно —
   `run_id`, `test_name` (из аргументов `jfr_to_graph.py`), сколько сэмплов и какой процент — и
   явно, но не извиняющимся тоном указывал, что абсолютное before/after ожидает подключения
   [011](011-relative-thresholds-and-multirun-diff.md); убрать фразу, которая сейчас буквально
   обесценивает находку как "not a measured comparison" без какой-либо воспроизводимой детали.
5. Не трогать `reports/sandbox/findings.json` на диске в рамках этой спеки — файл
   перегенерируется отдельным прогоном после того, как код смёржен (см. Acceptance criteria
   [004](004-findings-json-generator.md), которая уже описывает регенерацию).

## Files touched
- `skill/scripts/export_report.py` (функции `_channel_for`, `build_findings_from_anomalies`,
  новая таблица `ANOMALY_TYPE_TO_TAXONOMY_CODES`)

## Acceptance criteria
- [ ] `evidence.channel` для каждой находки — один из 5 значений enum `TASK/SUBMISSION.md`, ни
      одного изобретённого значения
- [ ] `evidence.after` — всегда число (не `null`), с честной пометкой в `how`, если это
      прогнозируемое, а не измеренное значение
- [ ] Находки с типами из `ANOMALY_TYPE_TO_TAXONOMY_CODES` дают многоэлементный `pdf_taxonomy`;
      остальные — как раньше, одноэлементный
- [ ] `evidence.how` содержит `run_id`/`test_name`/процент сэмплов вместо пустой отговорки
- [ ] Ни одно значение `family`/`channel`/`pdf_taxonomy` не хардкодит имя класса/метода песочницы
      (сохраняется требование из уже существующих спек)
- [ ] Regression: запуск `export_report.py --db-path <тестовая БД>` по-прежнему производит валидный
      JSON по всем прежним критериям [004](004-findings-json-generator.md)

## Dependencies
Зависит от [004](004-findings-json-generator.md) (чинит её реализацию). Пересекается с
[011](011-relative-thresholds-and-multirun-diff.md): 011 в будущем заменит заглушку `after` из
шага 2 реальным `compare_runs()`-значением, но 015 не блокирует и не блокируется 011 — обе спеки
независимо исполнимы.
