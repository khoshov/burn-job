# 010 — Правила в конфиг, устранение дублирования между категориями

## Problem

Найдено дословное дублирование Cypher-правил между разными `taxonomy_id`:
- `SAVE_IN_LOOP_UNBATCHED`: идентичный запрос в `t1_redundant_ops.py:23-28` (T1) и
  `t6_db_queries.py:46-51` (T6) — подтверждено эмпирически: одно и то же ребро вызова
  засчиталось дважды под разными категориями в нашем тестовом прогоне.
- string-concat правило: идентичный запрос в `t1_redundant_ops.py:46-51` (T1) и
  `t8_memory_bloat.py:46-51` (T8, до правки в [005](005-allocation-based-t4-t8.md)).

Кроме дублирования, все пороги (`count > 50`, `sampleCount > 100` и т.д.) и паттерны имён
зашиты в Python-код построчно — изменение порога требует правки кода и повторного код-ревью,
а не конфигурации.

## Goal

Единый источник правды для правил: YAML/JSON-конфиг с паттерном + порогом + метаданными,
каждое правило регистрируется ровно под одной основной категорией, вторичные категории (если
антипаттерн релевантен нескольким T) помечаются как `also_relevant_to`, а не дублируются как
отдельный Cypher-запрос.

## Non-goals

- Не переносить в конфиг статические (AST-based) детекторы из [008](008-static-callgraph-reachability-t5.md)/[009](009-static-pattern-detection-t1-t2-t3-t6.md)
  — у них нет прямого Cypher-эквивалента, конфиг касается только графовых (`analyzers/t*.py`) правил.
- Не менять формат вывода аномалий — только источник паттернов/порогов.

## Approach

1. `skill/scripts/rules/graph_rules.yaml` — список правил вида:
   ```yaml
   - id: SAVE_IN_LOOP_UNBATCHED
     primary_taxonomy: T6          # было продублировано в T1 и T6 — теперь только здесь
     also_relevant_to: [T1]
     category: DATABASE_QUERIES
     severity: CRITICAL
     match:
       edge: CALLS
       callee_method_contains: ["performSave", "save"]
       callee_class_contains: ["AbstractSaveEventListener"]
     threshold: { field: count, op: ">", value: 50 }
     description_template: "Method '{caller}' invokes individual entity save operations in loops ({count} samples). Missing JDBC batching."
   ```
2. Небольшой генерик-движок `skill/scripts/rule_engine.py`: читает `graph_rules.yaml`, для
   каждого правила строит Cypher-запрос по шаблону (`match.edge`/`callee_*_contains` →
   `WHERE ... CONTAINS ...`), выполняет, применяет `threshold`, форматирует `description_template`.
3. `analyzers/t1..t9_*.py` заменяются на тонкие обёртки: `analyze_t6(conn) = rule_engine.run(conn, taxonomy="T6")`
   — существующий интерфейс (`ANALYZER_REGISTRY` в `analyze_anomalies.py:36-46`) не меняется,
   так что вызывающий код не трогается.
4. Дубликаты (`SAVE_IN_LOOP_UNBATCHED`, string-concat) остаются в конфиге ровно одной записью
   каждый, с `primary_taxonomy` + `also_relevant_to` — при генерации `findings.json` ([004](004-findings-json-generator.md))
   это единая аномалия с несколькими тегами `pdf_taxonomy`, а не два независимых срабатывания.

## Files touched

- `skill/scripts/rules/graph_rules.yaml` (новый файл, переносит все текущие правила)
- `skill/scripts/rule_engine.py` (новый файл)
- `skill/scripts/analyzers/t1..t9_*.py` (упрощаются до вызова `rule_engine.run`)

## Acceptance criteria

- [ ] Все правила, которые сейчас работают in-line в `analyzers/t*.py`, воспроизведены в
      `graph_rules.yaml` один-в-один по результату (regression: прогон на demo-проекте до и
      после рефакторинга даёт одинаковый набор аномалий, кроме заведомых изменений из
      [005](005-allocation-based-t4-t8.md)/[006](006-leak-detection-t7.md)/[007](007-lock-contention-t9-and-regex-fix.md), если они уже применены).
- [ ] `SAVE_IN_LOOP_UNBATCHED` и string-concat встречаются в конфиге ровно один раз каждое.
- [ ] Изменение порога (например `count > 50` → `count > 30`) не требует правки `.py`-файлов —
      только `graph_rules.yaml`.
- [ ] `ANALYZER_REGISTRY` и публичный интерфейс `analyze_anomalies()` не меняются — внешние
      потребители (например [004](004-findings-json-generator.md)) не замечают рефакторинга.

## Dependencies

Технически не зависит от других спек, но по смыслу должна выполняться после того, как
[005](005-allocation-based-t4-t8.md)/[006](006-leak-detection-t7.md)/[007](007-lock-contention-t9-and-regex-fix.md)
уже поменяли логику T4/T7/T8/T9 — иначе придётся переносить в конфиг то, что тут же будет
переписано заново.
