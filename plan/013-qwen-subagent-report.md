# 013 — Qwen Code subagent: читаемый отчёт по findings.json

## Problem
`skill/SKILL.md` — нарративный документ для GigaCode-хакатона (см. `TASK/BRIEFING.md`), без
структурированного манифеста агента. Пайплайн детекта (`jfr_to_graph.py` → KùzuDB →
анализаторы → `export_report.py`) сегодня производит только `findings.json` — и это должно
остаться так. Но между "получить JSON" и "исправить код" нет промежуточного шага: никто не
превращает `findings.json` в читаемый отчёт для пользователя. Плюс пайплайн не обнаруживаем и
не вызываем из Qwen Code (открытый CLI-агент от Alibaba), который ищет сабагентов как
markdown-файлы с YAML frontmatter в `.qwen/agents/` (project-level) или `~/.qwen/agents/`
(user-level) — формат: `name`, `description` (обязательные), `model`, `approvalMode`, `tools`,
`disallowedTools` (опциональные), плюс системный промпт в теле файла.

## Goal
Создать `.qwen/agents/perf-findings-agent.md` — Qwen Code subagent, который читает
`findings.json` и составляет читаемый отчёт (без единой правки кода). Мутации файлов должны
быть структурно невозможны на этом этапе, не только "не рекомендованы" в промпте.

## Non-goals
- Не запускать сам детект — скрипты (`jfr_to_graph.py` → KùzuDB → анализаторы →
  `export_report.py`) остаются как есть и производят только `findings.json` (проверено:
  `export_report.py` `--output` по умолчанию пишет только `reports/sandbox/findings.json`).
  Трек 001–012 занимается точностью этого JSON, не эта спека.
- Не реализовывать применение фиксов к коду — это [014](014-qwen-subagent-fix-mode.md).
  013 намеренно не имеет write/shell инструментов вообще.
- Не строить MCP-сервер — отдельный, более тяжёлый путь интеграции; не в скоупе.
- Не удалять и не дублировать `SKILL.md` — он остаётся документацией для других хостов
  (GigaCode); новый файл — дополнительный, Qwen-Code-специфичный манифест.

## Approach
1. Frontmatter `.qwen/agents/perf-findings-agent.md`:
   - `name: perf-findings-agent`
   - `description`: "Reads an existing findings.json (produced by a prior JFR/profiler
     analysis step) and produces a human-readable report of detected Java/Spring performance
     antipatterns (taxonomy T1-T9). Use PROACTIVELY once findings.json exists."
   - `model: inherit` (модель родительской сессии Qwen Code составляет отчёт).
   - `approvalMode: plan` (analyze-only — файловые мутации структурно невозможны, это даёт
     платформенную гарантию поверх любых прompt-инструкций).
   - `tools`: allowlist `read_file`, `read_many_files` — намеренно **без** `write_file` и
     `run_shell_command`, чтобы даже при ошибке в промпте агент физически не мог ничего
     изменить.
2. Тело файла (системный промпт):
   - Прочитать `findings.json` (по умолчанию `reports/sandbox/findings.json`); на каждую
     находку — taxonomy-категория (T1-T9), расположение (файл/метод/строка, если есть source
     mapping — см. [003](003-source-mapping.md)), человекочитаемое объяснение проблемы,
     confidence; учитывать non-defect защиту раздела 7 (не показывать как дефект то, что
     отфильтровано — см. [012](012-non-defect-evidence-hardening.md), если уже реализовано).
   - Если `findings.json` отсутствует или устарел — сообщить, что сначала нужно выполнить шаг
     детекта (скрипты), не пытаться запускать их самостоятельно.
   - Явно указать в конце отчёта: "чтобы исправить эти находки, попросите меня явно" (задел
     под 014).
3. Кросс-ссылка: добавить короткую заметку в `skill/SKILL.md` о существовании
   `.qwen/agents/perf-findings-agent.md` как альтернативной точки входа под Qwen Code.
4. Обновить `plan/README.md`: новая фаза `P3 — интеграция с внешними CLI-агентами` со строкой
   на 013 (и заготовкой строки на 014); граф зависимостей: 013 независима от 001–012, но
   опирается на формат `findings.json` из [004](004-findings-json-generator.md).

## Files touched
- New: `.qwen/agents/perf-findings-agent.md`
- New: `plan/013-qwen-subagent-report.md`
- Modified: `plan/README.md` (новая фаза + граф зависимостей)
- Modified: `skill/SKILL.md` (короткая кросс-ссылка, 1-2 строки)

## Acceptance criteria
- [ ] `.qwen/agents/perf-findings-agent.md` парсится как валидный Qwen Code subagent
      (обязательные `name`+`description`; `approvalMode: plan` — валидное значение)
- [ ] `tools` allowlist содержит только `read_file`, `read_many_files` — нет `write_file`,
      нет `run_shell_command`
- [ ] Отчёт по находкам читаем и включает taxonomy-категорию, расположение, объяснение и
      confidence на каждую находку
- [ ] Системный промпт нигде не предлагает агенту самостоятельно запускать
      `jfr_to_graph.py`/`export_report.py`
- [ ] Файл обнаруживается Qwen Code (`/agents manage` или размещением в `.qwen/agents/`) без
      ошибок парсинга, если тестируемо в окружении
- [ ] `plan/README.md` согласованно обновлён (новая фаза + граф зависимостей)

## Dependencies
Не зависит от 001–012 по реализации (работает поверх любого корректного `findings.json`),
но опирается на формат, заданный [004](004-findings-json-generator.md). Блокирует
[014](014-qwen-subagent-fix-mode.md), которая расширяет тот же файл.
