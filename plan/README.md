# Спецификации доработки пайплайна детекции аномалий

Этот каталог — набор независимых спецификаций (spec-driven development) на доработку
пайплайна `skill/scripts/jfr_to_graph.py` → KùzuDB → `skill/scripts/analyzers/t1..t9*.py` →
`skill/scripts/non_defects.py` → `skill/scripts/export_report.py`.

## Зачем

Эмпирическая проверка пайплайна (прогон на свежем, не связанном с Hibernate Java-приложении)
показала, что почти все правила T1–T9 — это эвристики по подстрокам имён классов/методов
поверх CPU-графа вызовов, а не прямые измерения того, что описывает таксономия. Это не только
инженерная проблема: `TASK/SUBMISSION.md` прямо штрафует находки от правил, захардкоженных под
конкретный проект песочницы — а итоговый балл на 70% считается по скрытому `control`-проекту
с другим доменом и другими именами классов. Кроме того, `findings.json` сейчас пишется руками
в `export_report.py`, а не выводится из реального анализа графа.

Каждая спецификация ниже — самостоятельная задача: файл, взятый в одиночку, должен быть
исполним без необходимости поднимать весь этот контекст заново.

## Формат каждой спеки

`Problem` → `Goal` → `Non-goals` → `Approach` → `Files touched` → `Acceptance criteria` → `Dependencies`.

## Порядок выполнения (фазы)

### P0 — фундамент (разблокирует реальный findings.json и точность остальных фаз)
| # | Спека | Коротко |
|---|---|---|
| 1 | [001-native-jfr-parser.md](001-native-jfr-parser.md) | Нормальный парсер `.jfr` вместо скрейпинга текста `jfr print` |
| 2 | [002-graph-schema-extension.md](002-graph-schema-extension.md) | Новые типы узлов в KùzuDB: аллокации, retained-объекты, блокировки |
| 3 | [003-source-mapping.md](003-source-mapping.md) | Метод → файл/строка (нужно для реального findings.json) |
| 4 | [004-findings-json-generator.md](004-findings-json-generator.md) | findings.json из реального анализа, а не хардкод |

### P1 — де-хардкод самых рискованных анализаторов (T4, T7, T8, T9)
| # | Спека | Коротко |
|---|---|---|
| 5 | [005-allocation-based-t4-t8.md](005-allocation-based-t4-t8.md) | T4/T8 по реальным байтам аллокаций, не по числу вызовов |
| 6 | [006-leak-detection-t7.md](006-leak-detection-t7.md) | T7 по retained-объектам и тренду между прогонами |
| 7 | [007-lock-contention-t9-and-regex-fix.md](007-lock-contention-t9-and-regex-fix.md) | T9 по реальной длительности блокировок + фикс ложных срабатываний на JIT |
| 8 | [008-static-callgraph-reachability-t5.md](008-static-callgraph-reachability-t5.md) | T5 по статической недостижимости + нулевым сэмплам |

### P2 — статический анализ для оставшихся эвристик + системное укрепление
| # | Спека | Коротко |
|---|---|---|
| 9 | [009-static-pattern-detection-t1-t2-t3-t6.md](009-static-pattern-detection-t1-t2-t3-t6.md) | Статические детекторы для T1/T2/T3/T6 вместо имён |
| 10 | [010-rule-config-externalization.md](010-rule-config-externalization.md) | Правила — в конфиг, убрать дублирование между категориями |
| 11 | [011-relative-thresholds-and-multirun-diff.md](011-relative-thresholds-and-multirun-diff.md) | Относительные пороги + сравнение прогонов по runId |
| 12 | [012-non-defect-evidence-hardening.md](012-non-defect-evidence-hardening.md) | Раздел 7 — проверка реальных доказательств, а не текста описания |

### P3 — интеграция с внешними CLI-агентами
| # | Спека | Коротко |
|---|---|---|
| 13 | [013-qwen-subagent-report.md](013-qwen-subagent-report.md) | Qwen Code subagent: read-only отчёт по findings.json |
| 14 | [014-qwen-subagent-fix-mode.md](014-qwen-subagent-fix-mode.md) | Тот же subagent: режим фикса кода по явной просьбе пользователя |

### P0.1 — донастройка findings.json под схему SUBMISSION.md (после 004, до/параллельно с 011)
| # | Спека | Коротко |
|---|---|---|
| 15 | [015-findings-evidence-schema-compliance.md](015-findings-evidence-schema-compliance.md) | evidence.channel/after/pdf_taxonomy/how — привести в соответствие с enum и примером из TASK/SUBMISSION.md |

### P4 — сборка сдаваемого пакета
| # | Спека | Коротко |
|---|---|---|
| 16 | [016-submission-packaging.md](016-submission-packaging.md) | Неразрушающий скрипт сборки чистого пакета по структуре TASK/SUBMISSION.md, исключая dev-артефакты (plan/, examples/, TASK/, .qwen/, .claude/) |

## Граф зависимостей

```
001 ─┬─> 002 ─┬─> 005
     │        ├─> 006
     │        └─> 007
003 ─┴─> 004        
003 ────> 008 ────> 009
002,005,006,008 ──> 012
(любая спека) ────> 010, 011 (рефакторинг поверх существующих правил)
004 ────> 013 ────> 014 (P3 ортогональна 001-012, зависит только от формата findings.json)
004 ────> 015 (чинит evidence-поля 004; 011 позже заменит заглушку `after` из 015 реальным compare_runs())
(любая спека) ────> 016 (016 — ортогональная упаковка; перезапускается снимком после изменений в findings.json/MANIFEST.md/pr/)
```

## Итоговая проверка (после реализации всех спек)

Повторить прогон, уже сделанный вручную в этой сессии (см. `skill/scripts/verify_full_pipeline.py`
и профилирование тестового Java-приложения через async-profiler), и убедиться, что:
- `findings.json` формируется автоматически, а не написан руками;
- T4/T7/T8/T9 срабатывают на реальных данных аллокаций/retained-объектов/блокировок, а не на
  числе CPU-сэмплов как прокси;
- ложное срабатывание T9 на фреймах JIT-компилятора (`CompileBroker::compile_method`),
  обнаруженное в этой сессии, больше не воспроизводится;
- ни одно правило анализатора не ссылается на имя класса/метода, специфичное для песочницы.
