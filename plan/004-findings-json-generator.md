# 004 — Реальный генератор findings.json вместо хардкода

## Problem

`generate_burn_job_report()` в `skill/scripts/export_report.py:19-105` — это литерал: 4 находки
и 3 "не дефекта" вписаны в код руками и **побайтово совпадают** с `reports/sandbox/findings.json`.
Функция никогда не обращается ни к KùzuDB, ни к `analyze_anomalies()` — реальный анализ графа
(T1-T9 + Раздел 7) существует и работает (подтверждено эмпирическим прогоном в этой сессии), но
никак не связан с тем, что реально сдаётся на проверку.

## Goal

`export_report.py` строит `findings.json` из фактического вывода `analyze_anomalies()`, а не из
захардкоженного словаря, сохраняя точную схему, которую требует `TASK/SUBMISSION.md`.

## Non-goals

- Не менять формат/схему `findings.json` — она зафиксирована судейским скриптом.
- Не добавлять новые источники `evidence.before/after` сверх того, что уже даёт граф — это
  дальше улучшается в [011](011-relative-thresholds-and-multirun-diff.md); здесь достаточно
  честно прокинуть то, что уже есть (`sample_count`/`percentage`), пометив как приблизительное
  там, где нет прямого before/after сравнения.

## Approach

1. Новая функция `build_findings_from_anomalies(anomalies: list) -> dict`:
   - берёт список аномалий от `analyze_anomalies.analyze_anomalies(db_path)` (только со
     `status == "DEFECT"` — non-defects идут в `checked_but_not_an_issue`);
   - для каждой аномалии резолвит `caller`/`callee` через `resolve_source_location()` из
     [003](003-source-mapping.md); если у обоих полей есть локация — берётся `callee` (место,
     где реально происходит проблемное действие), иначе `caller`; если локация не резолвится
     ни для одного (оба фрейма — JDK/framework) — аномалия исключается из `findings` и логируется
     как пропущенная (см. acceptance criteria);
   - маппит `taxonomy_id`/`category` анализатора в `family` (`db`/`cpu`/`memory`/`algo`/`redundant`)
     по фиксированной таблице соответствия (T1→redundant, T2→algo, T3/T4/T7/T8→memory, T6→db,
     T9→cpu, T5 — по типу конкретной аномалии);
   - `mechanism` берётся из поля `description` аномалии (оно уже человекочитаемо описывает
     механизм, как и требует `SUBMISSION.md`: "не «медленный код», а механизм");
   - `evidence.channel`/`before`/`after` — из `sample_count`/`percentage`, с явной пометкой
     `"how"`, что это профилировочные сэмплы, а не прямое измерение (пока не подключены
     спеки 005/006/011 с более точными данными).
2. Для `checked_but_not_an_issue` — маппинг `NON_DEFECT`-аномалий в формат `{file, claim, why_not}`
   с `why_not` из `non_defect_justification`.
3. `main()` в `export_report.py` принимает `--db-path` (вместо возврата статичного словаря) и
   пишет результат в `reports/sandbox/findings.json`.

## Files touched

- `skill/scripts/export_report.py` (заменить `generate_burn_job_report`, добавить CLI-аргумент
  `--db-path`)
- `skill/scripts/source_mapping.py` (использование, без изменений интерфейса из спеки 003)

## Acceptance criteria

- [ ] Запуск `python3 export_report.py --db-path <тестовая БД>` производит валидный JSON по схеме
      `TASK/SUBMISSION.md` (обязательные поля `file`, `line_from`, `family`, `pdf_taxonomy`,
      `mechanism`, `fix` присутствуют на каждой находке).
- [ ] На БД, полученной из прогона на demo-проекте (`badhibernate`), находки пересекаются по
      сути (не обязательно один-в-один) с текущим ручным `reports/sandbox/findings.json` —
      N+1, save-in-loop, in-memory filter, full-entity-fetch должны быть узнаваемы среди
      сгенерированных находок.
- [ ] Аномалии без резолвящейся локации не попадают в `findings` молча — они логируются
      (например в `runlog/agent_run.log`) с причиной пропуска.
- [ ] Ни одна находка не содержит текста, буквально скопированного из старого хардкода —
      весь текст выводится из реального `description`/`mechanism` аномалии.

## Dependencies

[003](003-source-mapping.md) — обязателен для `file`/`line_from`/`line_to`.
