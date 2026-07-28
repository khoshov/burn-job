# Burn Job — Performance Optimization Pipeline & Codebase Refactoring Engine

**Версия:** 0.1.0 | **Python:** >= 3.10

Автономный пайплайн для статического и динамического анализа производительности Java-приложений с автоматической генерацией оптимизированного кода. Сочетает графовую аналитику (KùzuDB), статический анализ байткода, профилирование через async-profiler / JFR и LLM-генерацию исправлений.

---

## Стек технологий

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| Язык | Python >= 3.10 | Оркестрация и аналитика |
| База данных | KùzuDB (встраиваемая) | Графовый движок: хранение стектрейсов, вызовов, SQL-запросов |
| LLM | OpenAI-совместимые (DeepSeek, GigaChat, OpenAI) | Генерация кода и оценка вариантов |
| Шаблонизатор | Jinja2 | Промпты для LLM |
| Статический анализ | `javap` (байткод), AST (исходники) | Построение графа вызовов, поиск паттернов |
| Профилирование | async-profiler / JFR (Java) | Сбор CPU, allocation, contention событий |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                          burn-job CLI                                │
│  scan │ ingest │ run-cycle                                          │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────────┐
│                    AutonomousOrchestrator (8-step cycle)             │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ Сканер  │ │Генератор │ │ Загрузка │ │ Инжест  │ │ Анализатор│ │
│  │контрол- │ │тестов    │ │ тестов   │ │профайла │ │ T1-T9     │ │
│  │леров    │ │нагрузки  │ │          │ │в KùzuDB │ │           │ │
│  └─────────┘ └──────────┘ └──────────┘ └──────────┘ └─────┬─────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────┴─────┐ │
│  │ LLM      │ │Верифика-│ │ Экспорт  │ │  Static Analysis     │ │
│  │цикл     │ │ция сборки│ │ отчёта   │ │  (javap, AST, regex) │ │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Трёхуровневая архитектура анализа

1. **Статический слой (исходный код/AST):**
   - Детекторы: N+1, Full Fetch для existence check, Nested Loops, Duplicate Methods
   - Анализ сложности: глубина вложенности, линейные поиски в циклах
   - Оценка object layout: статическая эвристика полей

2. **Байткод-слой (`javap`):**
   - Построение полного графа вызовов (call graph)
   - Вычисление reachability (BFS от entry points)
   - Обнаружение dead code (статистически невызываемые методы с 0 сэмплами)

3. **Динамический слой (профайлер / KùzuDB):**
   - Инжест collapsed-формата async-profiler в графовую БД
   - 9 таксономических анализаторов (T1–T9) через Cypher-запросы
   - Классификация non-defect (ND-1 – ND-7)
   - Differential analysis: сравнение baseline vs candidate run

---

## Установка

```bash
# Клонирование репозитория
git clone <repo-url>
cd burn-job

# Установка в редактируемом режиме (рекомендуется для разработки)
pip install -e .

# Или через uv
uv pip install -e .
```

### Зависимости

Обязательные:
- `kuzu` — встраиваемая графовая БД
- `jinja2` — шаблонизация промптов (если не установлен — используется JSON fallback)

Опциональные:
- `openai` — вызов LLM через API

---

## CLI-команды

### `burn-job scan`

Сканирует Java-контроллеры Spring на наличие REST-эндпоинтов.

```bash
burn-job scan --src ./java/src/main/java
```

**Аргументы:**

| Аргумент | По умолчанию | Описание |
|----------|-------------|----------|
| `--src` | `config.REPO_ROOT / 'src/main/java'` | Путь к Java-исходникам |

**Выход:** JSON-список `EndpointInfo` с путём, методом, контроллером, файлом и строкой.

### `burn-job ingest`

Загружает профилировочные данные (collapsed-формат async-profiler) в KùzuDB.

```bash
burn-job ingest --profile app_profiling_full.collapsed --db profiler_graph.db
```

**Аргументы:**

| Аргумент | По умолчанию | Описание |
|----------|-------------|----------|
| `--profile` | `config.DEFAULT_PROFILE_PATH` | Путь к collapsed-файлу |
| `--db` | `config.DEFAULT_DB_PATH` | Путь к файлу базы данных KùzuDB |

**Процесс инжеста:**
- Парсинг строк `frame1;frame2;... N`
- MERGE узлов `Method` (deduplicated по FQN)
- CREATE рёбер `CALLS` с подсчётом сэмплов
- Создание узлов `SqlStatement` и рёбер `EXECUTES` при наличии SQL-фреймов

### `burn-job run-cycle`

Запускает полный автономный 8-шаговый цикл оптимизации.

```bash
burn-job run-cycle --db profiler_graph.db --profile app_profiling_full.collapsed --host http://localhost:8080 --online
```

**Аргументы:**

| Аргумент | По умолчанию | Описание |
|----------|-------------|----------|
| `--db` | `config.DEFAULT_DB_PATH` | Путь к KùzuDB |
| `--profile` | `config.DEFAULT_PROFILE_PATH` | Путь к collapsed-файлу |
| `--host` | `http://localhost:8080` | Базовый URL целевого приложения |
| `--online` | `False` | Флаг: использовать LLM API (иначе — offline regex-рефакторинг) |

**8-шаговый цикл:**

| Шаг | Компонент | Описание |
|-----|-----------|----------|
| 1 | `ControllerScanner` | Сканирование REST-контроллеров |
| 2 | `LoadtestGenerator` | Генерация скрипта нагрузочного теста |
| 3 | API Load Test | Исполнение теста (50 коннектов, 5 сек) |
| 4 | `KuzuGraphStore.ingest_profile` | Инжест профайла в граф |
| 5 | Taxonomy Analysts (T1–T9) | Детекция аномалий |
| 6–7 | `iterative_agent_loop` | LLM-цикл рефакторинга (генерация → компиляция → оценка) |
| 8 | Maven Verify | Проверка сборки `mvn test-compile` |

---

## Система таксономии T1–T9

Девять категорий дефектов производительности, каждый со своим анализатором:

| ID | Категория | Файл | Что детектит | Метод |
|----|-----------|------|-------------|-------|
| **T1** | Redundant Operations | `t1_redundant_ops.py` | Избыточные конкатенации строк в циклах | Cypher-правило `EXCESSIVE_STRING_CONCAT` |
| **T2** | Inefficient Algorithms | `t2_inefficient_algos.py` | Линейные поиски в циклах; квадратичные вложенные циклы | Cypher-правило + кастомный Cypher |
| **T3** | Improper Function Usage | `t3_improper_func_usage.py` | Тяжёлая загрузка entity; full fetch для existence check | Cypher-правила |
| **T4** | Data Layout & Allocation | `t4_data_layout.py` | Array allocation pressure; boxing overhead; wasted field padding | Cypher + статический анализ object layout |
| **T5** | Redundant Checks | `t5_redundant_checks.py` | Dead code (unreachable + 0 samples); untested code; duplicate validation | Call graph BFS + статический доступ |
| **T6** | Database Queries | `t6_db_queries.py` | N+1 queries; save in loop unbatched; connection pool starvation | Cypher-правила |
| **T7** | Memory Leaks | `t7_memory_leak.py` | Retained object accumulation; unbounded growth trend; unbounded cache | JFR OldObjectSamples + cross-run diff |
| **T8** | Memory Bloat | `t8_memory_bloat.py` | In-memory filtering; excessive string allocations; bounded collections | Stream API + allocation bytes анализ |
| **T9** | CPU Hotspots | `t9_cpu_hotspots.py` | Thread lock contention; top CPU methods; regex recompile | MonitorBlock + топ-сэмплы |

### Классификация Non-Defect (ND-1 – ND-7)

После детекции аномалии проходят фильтр non-defect, исключающий ложные срабатывания:

| ND-ID | Название | Механизм верификации |
|-------|---------|---------------------|
| ND-1 | Field ordering | Статическая оценка `object_layout.py` |
| ND-2 | Bounded quadratic | Поиск `@Max` / `Math.min` в исходниках |
| ND-3 | Bounded cache | Cross-run сравнение retained объектов |
| ND-4 | Bounded request collection | Анализ рёбер графа (HTTPServletRequest context) |
| ND-5 | Microbenchmark noise | Единичные сэмплы, ratio < threshold |
| ND-6 | Code style | Pattern matching / Stream API без аллокаций |
| ND-7 | Untested coverage gap | Call graph: reachable, 0 samples, нет тестов |

---

## LLM-агент

### Режимы работы

1. **Offline (по умолчанию):** Детерминированные regex-замены без вызова API. Преобразования:
   - Save in Loop → `saveAll()` с batching
   - N+1 → `JOIN FETCH`
   - String concat → `StringBuilder`
   - Linear search → `HashSet`

2. **Online (`--online`):** Вызов LLM через OpenAI-совместимый API. Формирует промпты на основе:
   - `generator_prompt.jinja2` — генерация оптимизированного кода
   - `evaluator_prompt.jinja2` — оценка и улучшение сгенерированного кода
   - `error_prompt.jinja2` — исправление ошибок компиляции

3. **Multi-variant:** Генерация 3+ вариантов с ранжированием через:
   - HTTP-бенчмарки (SQL count, latency)
   - JFR-профилирование (CPU samples)
   - KùzuDB Cypher evaluation (веса сэмплов)

### Системные промпты

- `SYSTEM_PROMPT` — оптимизация Java 21 / Spring Boot 3
- `SYSTEM_MULTI_VARIANT_PROMPT` — генерация 3+ вариантов с тегом `[VARIANT_N]`

---

## Графовый движок KùzuDB

### Схема данных

```
Nodes:
  ─ Method {id, fqn, className, methodName, descriptor, isEntryPoint, isTest, ...}
  ─ SqlStatement {id, text, type}
  ─ Issue {id, taxonomy_id, category, type, severity, ...}

Relationships:
  ─ (m1)-[:CALLS {count, runId}]->(m2)
  ─ (m)-[:EXECUTES {runId}]->(sql)
  ─ (m)-[:HAS_DEFECT {runId}]->(issue)
```

### Структура правил (`rules/graph_rules.yaml`)

13 предопределённых Cypher-правил:

| Rule ID | Taxonomy | Тип узла | Паттерн |
|---------|----------|---------|---------|
| `SAVE_IN_LOOP_UNBATCHED` | T6, T1 | Edge | `.save(` в цикле |
| `EXCESSIVE_STRING_CONCAT` | T1, T8 | Edge | `StringBuilder` в цикле |
| `LINEAR_SEARCH_IN_LOOP` | T2 | Edge | `List.contains/indexOf` в цикле |
| `HEAVY_ENTITY_FETCH` | T3 | Method | Entity → DTO конвертация |
| `FULL_FETCH_FOR_EXISTENCE_CHECK` | T3 | Edge | `findAll()` → `isEmpty()` |
| `N_PLUS_ONE_QUERIES` | T6 | Edge | Lazy collection init |
| `CONNECTION_POOL_STARVATION` | T6 | Edge | `HikariPool.getConnection()` wait |
| `ARRAY_ALLOCATION_PRESSURE` | T4 | Method | `new byte[N]` с N > 10K |
| `UNBOUNDED_CACHE_OR_COLLECTION_GROWTH` | T7 | Edge | `Map.put` / `List.add` |
| `BOUNDED_REQUEST_COLLECTION` | T8 | Edge | API-bounded collections |
| `CPU_HOTSPOT_METHOD` | T9 | Method | Top CPU methods > 0.85% |
| `MICROBENCHMARK_REGEX_COMPILE` | T9 | Edge | `Pattern.compile` (исключая Global) |

---

## Модели данных

### `EndpointInfo`
```python
@dataclass
class EndpointInfo:
    path: str           # /api/demo/n-plus-one/bad
    http_method: str    # GET
    controller_class: str  # AntipatternController
    method_name: str    # getDepartmentsSubOptimal
    file_path: str      # src/main/java/.../AntipatternController.java
    line_number: int    # 42
    query_params: list[str]
```

### `Anomaly` / `Finding`
```python
@dataclass
class Anomaly:
    taxonomy_id: str     # T6
    category: str        # N_PLUS_ONE_QUERIES
    type: str            # edge / method
    caller: str          # FQN вызывающего метода
    callee: str          # FQN вызываемого метода
    sample_count: int
    status: str          # open / non_defect
    non_defect_rule: str  # ND-3
    details: dict

@dataclass
class Finding:
    id: str
    taxonomy_id: str
    category: str
    type: str
    title: str
    description: str
    file: str
    line: int
    status: str
    evidence: dict
```

### `CodeVariant` / `ScoringResult`
```python
@dataclass
class CodeVariant:
    variant_id: str         # v1, v2, v3
    target_file: str
    code_content: str
    compiles: bool
    compile_error: str | None

@dataclass
class ScoringResult:
    variant_id: str
    latency_p95_delta_pct: float
    rps_delta_pct: float
    gc_delta_pct: float
    score: float
    is_winner: bool
```

### `LatencyStats` / `MicrometerMetrics`
```python
@dataclass
class LatencyStats:
    p50: float
    p95: float
    p99: float

@dataclass
class MicrometerMetrics:
    endpoint: str
    rps: float
    latency: LatencyStats
    gc_allocations_mb: float
    error_count: int
    total_requests: int
```

---

## Формула оценки

Композитный score для ранжирования вариантов оптимизации:

```
Score = 0.6 * ΔLatency_p95% + 0.3 * ΔRPS% + 0.1 * ΔGC%
```

Где Δ — относительное улучшение между baseline и candidate (положительное значение = улучшение).

---

## Скрипты и утилиты

### Полная структура файлов

```
src/
├── __init__.py                        # Версия пакета
├── cli.py                             # CLI entry point (3 команды)
├── config.py                          # Глобальные константы и пути
├── logging_config.py                  # Централизованная настройка логирования
│
├── core/
│   ├── orchestrator.py                # AutonomousOrchestrator (8-шаговый цикл)
│   ├── generator.py                   # ControllerScanner + LoadtestGenerator
│   ├── evaluator.py                   # ScoringEvaluator (весовая формула)
│   └── graph_store.py                 # KuzuGraphStore (обёртка KùzuDB)
│
├── analyzers/
│   ├── t1_redundant_ops.py            # T1: избыточные операции
│   ├── t2_inefficient_algos.py        # T2: неэффективные алгоритмы
│   ├── t3_improper_func_usage.py      # T3: неправильное использование функций
│   ├── t4_data_layout.py              # T4: размещение данных и аллокации
│   ├── t5_redundant_checks.py         # T5: мёртвый код и избыточные проверки
│   ├── t6_db_queries.py               # T6: ошибки БД-запросов
│   ├── t7_memory_leak.py              # T7: утечки памяти
│   ├── t8_memory_bloat.py             # T8: раздувание памяти
│   └── t9_cpu_hotspots.py             # T9: CPU hotspots и contention
│
├── models/
│   ├── endpoint.py                    # EndpointInfo dataclass
│   ├── finding.py                     # Anomaly + Finding dataclasses
│   ├── metrics.py                     # LatencyStats + MicrometerMetrics
│   └── variant.py                     # CodeVariant + ScoringResult
│
├── llm/
│   └── __init__.py                    # Реэкспорт LLMAgent
├── detection/
│   ├── __init__.py                    # Реэкспорт детекторов
│   └── base.py                        # BaseDetector + утилиты
├── loop/
│   └── __init__.py                    # Реэкспорт iterative_loop
├── report/
│   └── __init__.py                    # Реэкспорт билдеров отчётов
├── prompts/
│   ├── generator_prompt.jinja2        # Промпт генерации кода
│   ├── evaluator_prompt.jinja2        # Промпт оценки кода
│   └── error_prompt.jinja2            # Промпт исправления ошибок
└── rules/
    └── graph_rules.yaml               # 13 Cypher-правил

# Автономные скрипты (top-level):
├── llm_agent.py                       # LLM-агент (offline + online)
├── analyze_anomalies.py               # Оркестратор T1–T9 + static detectors
├── static_callgraph.py                # Статический граф вызовов (javap)
├── static_pattern_detectors.py        # Структурные детекторы (N+1, nested loops, etc.)
├── jfr_to_graph.py                    # Инжест профайла в KùzuDB (CLI)
├── iterative_agent_loop.py            # SysLLMatic итеративный цикл
├── complexity_analyzer.py             # AST-анализ сложности Java-кода
├── source_mapping.py                  # FQN → исходный файл/строка
├── object_layout.py                   # Статический object layout estimator
├── differential_analysis.py           # Cross-run сравнение (baseline vs candidate)
├── non_defects.py                     # Non-defect классификация (ND-1 – ND-7)
├── rule_engine.py                     # Generic Cypher rule engine
├── export_report.py                   # Генератор findings.json
├── benchmark_variants.py              # Мульти-вариантный HTTP benchmark
├── evaluate_variants_via_kuzu.py      # Cypher evaluation вариантов
├── multi_variant_jfr_evaluator.py     # JFR + HTTP evaluator
├── compare_runs.py                    # Устаревший differential analyzer
├── generate_api_loadtests.py          # Генератор нагрузочных тестов
├── verify_full_pipeline.py            # Smoke test пайплайна
└── run_full_autonomous_cycle.py       # Обёртка AutonomousOrchestrator
```

### Ключевые точки расширения

1. **Добавление нового анализатора T10+**: создать `analyzers/t10_*.py`, импортировать в `analyze_anomalies.py`, добавить правило в `rules/graph_rules.yaml`.
2. **Новое Cypher-правило**: добавить YAML-блок в `graph_rules.yaml` с match/exclude/threshold.
3. **Новый статический детектор**: реализовать в `static_pattern_detectors.py` или отдельном модуле, зарегистрировать в `detection/__init__.py`.
4. **Новый ND-фильтр**: добавить правило в `non_defects.py` с верификацией и confidence.

---

## Пример пайплайна

```bash
# Шаг 1: Установка пакета
pip install -e .

# Шаг 2: Сканирование REST-контроллеров
burn-job scan --src ./java/src/main/java

# Шаг 3: Запуск полного автономного цикла
burn-job run-cycle --profile ./profiles/app.collapsed --online

# Или пошагово:
# 3a: Инжест профайла
burn-job ingest --profile ./profiles/app.collapsed --db ./analysis.db

# 3b: Ручной запуск анализаторов
python -m src.analyze_anomalies --db-path ./analysis.db --json

# 3c: LLM-рефакторинг
python -m src.llm_agent --finding '{"taxonomy_id":"T6","category":"N_PLUS_ONE_QUERIES",...}'
```

---

## Лицензия

MIT
