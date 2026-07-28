# 014 — Qwen Code subagent: режим фикса по явной просьбе

## Problem
[013](013-qwen-subagent-report.md) даёт безопасный, read-only агент-отчёт, но по
подтверждённому воркфлоу пользователя тот же агент должен уметь применять taxonomy-aware фиксы
к коду, когда его явно об этом просят — аналогично циклу fix+verify в `llm_agent.py`, но с
рассуждением моделью самого Qwen Code, а не вторым внешним LLM-вызовом. Сейчас у
`.qwen/agents/perf-findings-agent.md` (создан в 013 в read-only форме) нет ни инструментов для
записи, ни логики фиксов.

## Goal
Расширить `.qwen/agents/perf-findings-agent.md` (созданный в 013) режимом фикса: по явной
просьбе пользователя — применить фикс по категории находки и верифицировать через
`mvn test-compile`, с retry при неудаче.

## Non-goals
- Не менять поведение по умолчанию из 013 — без явной просьбы агент остаётся read-only
  отчётом; это не переключатель конфигурации, а обязательное поведение "по умолчанию".
- Не менять логику анализаторов/таксономии T1–T9 и не запускать сам детект.
- Не создавать отдельный второй файл агента — расширяется тот же
  `perf-findings-agent.md`, чтобы делегирование оставалось на одну точку входа.
- Не реализовывать нативную интеграцию Qwen-модели как LLM-провайдера внутри `llm_agent.py` —
  рассуждение о фиксах делает сам агент Qwen Code через собственную модель; `llm_agent.py
  --offline` остаётся только референсной логикой фиксов, которую системный промпт переносит
  как инструкцию.

## Approach
1. Frontmatter-изменения в `.qwen/agents/perf-findings-agent.md`:
   - `approvalMode`: `plan` → `auto-edit` (нужно, чтобы мутации файлов вообще были возможны).
   - `tools`: добавить `write_file`, `run_shell_command` (шелл — только для
     `mvn test-compile`).
   - `description`: дополнить фразой "Only applies code fixes if the user explicitly asks to
     fix/refactor the flagged issues."
2. Добавить в системный промпт отдельный, явно озаглавленный раздел "Режим фикса (только по
   явной просьбе)":
   - Правила фиксов по категориям (перенос из `SKILL.md` / `llm_agent.py --offline`): T1/T6 →
     `saveAll()` вместо цикла `save()`; T2/T6 → `JOIN FETCH` JPQL вместо N+1; T3/T4 → Spring
     Data projection интерфейсы вместо полных сущностей; T8/T3 → перенос `WHERE`/`Pageable`
     в БД.
   - После каждой правки — `mvn test-compile`; при ошибке — reflect & retry (аналог
     `H -- Fail --> J["Reflect & Retry"] --> B` из mermaid-диаграммы `SKILL.md`); логировать
     шаги в `runlog/agent_run.log`.
   - Явное правило: даже имея write/shell-инструменты, агент обязан использовать их только
     если сообщение пользователя явно просит исправить/зафиксить/отрефакторить находки —
     иначе оставаться в read-only режиме отчёта из 013.
3. Обновить `plan/README.md`: добавить строку 014 в фазу `P3`, граф зависимостей —
   `013 ──> 014`.

## Files touched
- Modified: `.qwen/agents/perf-findings-agent.md` (frontmatter + новый раздел системного
  промпта)
- New: `plan/014-qwen-subagent-fix-mode.md`
- Modified: `plan/README.md` (строка 014 + граф зависимостей)

## Acceptance criteria
- [ ] Фикс запускается только при явной просьбе пользователя; без неё поведение идентично 013
      (read-only отчёт)
- [ ] Правила фиксов по каждой категории T1-T9 согласованы с `SKILL.md` / `llm_agent.py
      --offline`
- [ ] После каждой правки выполняется `mvn test-compile` с retry при ошибке
- [ ] `approvalMode: auto-edit` и обновлённый `tools` allowlist валидны по схеме Qwen Code
- [ ] `plan/README.md` согласованно обновлён (строка 014 + граф зависимостей)

## Dependencies
Зависит от [013](013-qwen-subagent-report.md) — расширяет файл, созданный этой спекой.
Опирается на формат `findings.json` из [004](004-findings-json-generator.md), как и 013.
