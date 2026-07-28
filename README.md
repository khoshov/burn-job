# Burn Job — Performance Optimization Pipeline & Codebase Refactoring Engine

**Версия:** 0.1.0 | **Python:** >= 3.10 | **Лицензия:** MIT

Автономный агентный пайплайн для статического анализа байткода, инжеста динамических трейсов профайлера и LLM-управляемого рефакторинга производительности Java-приложений.

---

## Содержание

1. [Описание проекта](#-описание-проекта)
2. [Архитектура](#-архитектура)
3. [Матрица зависимостей](#🛠-матрица-зависимостей)
4. [Установка и настройка](#-установка-и-настройка)
5. [Конфигурация](#-конфигурация-окружения)
6. [Детекторы: подробное описание](#-детекторы-t1t9-подробное-описание)
   - [Общая архитектура детекции](#общая-архитектура-детекции)
   - [Сводная таблица способов обнаружения](#сводная-таблица-способов-обнаружения)
   - [Принцип работы каждого детектора](#принцип-работы-каждого-детектора)
   - [Cross-cutting композитные детекторы](#cross-cutting-композитные-детекторы)
   - [Dual-evidence слияние (граф БД + статика)](#dual-evidence-слияние)
7. [Правила `graph_rules.yaml`](#-правила-graph_rulesyaml)
8. [8-этапный цикл автономной оптимизации](#🔄-8-этапный-цикл-автономной-оптимизации)
9. [Использование CLI](#-использование-cli)
10. [Scoring Function](#-scoring-function)
11. [Тестирование](#-запуск-тестов)
12. [Лицензия](#-лицензия)

---

## 📋 Описание проекта

**Burn Job** — полностью автономная система анализа и оптимизации производительности Java-приложений (REST-сервисы на Spring Boot). Пайплайн комбинирует **два подхода обнаружения проблем**:

1. **Графовая база данных (KùzuDB)**: трейсы async-profiler/JFR инжестятся во встраиваемую графовую СУБД. Cypher-запросами анализируются call-графы, hotspot-методы, SQL-запросы, аллокации памяти.
2. **Статический анализ (AST + байткод)**: Java-исходники парсятся напрямую — поиск паттернов N+1, вложенных циклов, duplicate-методов, existence-check без COUNT, layout полей.

Результаты **обоих подходов cross-референсятся**: если один и тот же дефект найден и в графе БД, и в исходниках — финальный finding получает повышенный confidence и двойное доказательство. Если только в одном источнике — confidence ниже, а источник маркируется.

После детекции запускается **LLM-агентный цикл рефакторинга**: для каждого дефекта генерируется оптимизированный Java-код, проверяется через `mvn test-compile` и оценивается прирост производительности.

---

## 🏛 Архитектура

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                burn_job.cli                                         │
│                     (dispatch: scan, ingest, run-cycle, analyze)                     │
└─────────────────────────────────┬───────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────────────┐
│                            burn_job.pipeline                                        │
│  AutonomousOrchestrator (8-step cycle)                                              │
│  ├─ ControllerScanner — сканирование @RestController в Java AST                    │
│  ├─ LoadtestGenerator — генерация python-скриптов нагрузочного тестирования         │
│  └─ Scorer — расчёт качества вариантов (latency/RPS/GC)                            │
└──────────────────┬──────────────────────────────────────────────┬───────────────────┘
                   │                                              │
┌──────────────────▼──────────────────────────────────┐ ┌─────────▼───────────────────┐
│                 burn_job.detectors                   │ │      burn_job.graph         │
│                                                      │ │                             │
│  ┌─────────────────────────────────────┐            │ │  KuzuGraphStore — клиент    │
│  │     Orchestrator (analyze_anomalies) │            │ │  KùzuDB: инициализация      │
│  │  ┌─────────────────────────────────┐│            │ │  схемы, MERGE узлов,        │
│  │  │  Шаг 1: KuzyDB analyzers (T1-9) ││            │ │  профилирование.ingest()    │
│  │  │  (rule_engine.run() по           ││            │ │                             │
│  │  │   graph_rules.yaml +             ││            │ │  Cypher-схема:              │
│  │  │   taxonomy/*.py)                 ││            │ │  • Method (name, class)     │
│  │  ├─────────────────────────────────┤│            │ │  • SqlStatement (hash, sql) │
│  │  │  Шаг 2: Static pattern detectors││            │ │  • Issue (id, taxonomy,     │
│  │  │  (patterns.py: N+1, nested      ││            │ │    severity)                │
│  │  │   loops, duplicates, etc.)       ││            │ │  • CALLS (count, percent)   │
│  │  ├─────────────────────────────────┤│            │ │  • EXECUTES (count)         │
│  │  │  Шаг 3: _merge_dual_evidence()   ││            │ │  • HAS_DEFECT (severity)    │
│  │  │  cross-референс графа и статики  ││            │ └─────────────────────────────┘
│  │  ├─────────────────────────────────┤│            │
│  │                                      │            │
│  │  _shared.py — консолидированные      │            │
│  │  утилиты (iter_java_files,           │            │
│  │  strip_comments, scan_braces,        │            │
│  │  iter_method_bodies)                  │            │
│  └──────────────────────────────────────┘            │
└──────────────────┬───────────────────────────────────┴──────────────────────────────┘
                   │
                   └──────────────────┬──────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────────────┐
│                            burn_job.domain                                         │
│  Finding, Anomaly, Severity, SourceLocation, EndpointInfo, Metric,                 │
│  CodeVariant, ScoringResult, PipelineContext                                       │
└─────────────────────────────────────┬──────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────────────┐
│                            burn_job.core                                           │
│  Config (environment vars), Exceptions (hierarchy), Logging (structured),          │
│  Protocols (DetectorProtocol, StoreProtocol, ReportBuilderProtocol)                │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Матрица зависимостей

### Python-библиотеки (`pyproject.toml`)

| Зависимость | Версия | Назначение |
|-------------|--------|-----------|
| **`kuzu`** | `>= 0.3.0` | Встраиваемая графовая СУБД KùzuDB: хранение стектрейсов, узлов методов, графов вызовов (CALLS) и SQL-запросов |
| **`jinja2`** | `>= 3.0.0` | Шаблонизатор промптов для LLM-агента генерации оптимизированных вариантов кода |
| **`pyyaml`** | `>= 6.0` | Парсинг `graph_rules.yaml` — externalized rule definitions для Cypher-запросов |
| **`pytest`** *(test)* | `>= 8.0` | Основной фреймворк запуска unit, integration и contract тестов |
| **`pytest-cov`** *(test)* | `>= 5.0` | Сборщик покрытия кода тестами |

### Системное окружение и внешние инструменты

| Инструмент | Минимальная версия | Назначение |
|-----------|-------------------|-----------|
| **Python** | `>= 3.10` | Основной язык оркестрации и аналитических модулей |
| **Java JDK** | `>= 17` | Среда компиляции и выполнения целевого Java-приложения |
| **Apache Maven** | `>= 3.8` | Автоматическая компиляция (`mvn test-compile`) и верификация вариантов кода |
| **async-profiler** | `>= 2.9` | Профилирование CPU, allocations, locks. Формат: `.collapsed` (folded stacks) |
| **JFR (JDK Flight Recorder)** | Встроен в JDK 17+ | Альтернативный источник профилировочных данных |

### Структура репозитория

```
burn-job/
├── java/                          # Целевое Java-приложение
│   ├── src/main/java/             # Исходники Java
│   └── target/classes/            # Скомпилированные классы (javap-анализ)
├── src/burn_job/                  # Python-пакет оркестрации
│   ├── core/                      # Конфиг, логи, протоколы, исключения
│   ├── domain/                    # Доменные модели (Finding, Anomaly, ...)
│   ├── detectors/                 # Детекторы (основной модуль)
│   │   ├── _shared.py             # Консолидированные утилиты
│   │   ├── rule_engine.py         # RuleEngine + Cypher-выполнение graph_rules.yaml
│   │   ├── patterns.py            # Статические AST-детекторы
│   │   ├── complexity.py          # AST-анализ сложности (O(1)..O(N³))
│   │   ├── callgraph.py           # Статический граф вызовов через javap
│   │   ├── object_layout.py       # Анализ layout полей Java-классов
│   │   ├── differential.py        # Cross-run сравнение (baseline vs candidate)
│   │   ├── source_mapping.py      # Method FQN → source file/line
│   │   ├── non_defects.py         # Классификация non-defect (Section 7 rules)
│   │   ├── orchestrate.py         # Главный оркестратор (analyze_anomalies)
│   │   └── taxonomy/              # T1-T9 анализаторы (обёртки над rule_engine.py)
│   ├── graph/                     # Интеграция с KùzuDB
│   ├── pipeline/                  # 8-этапный пайплайн
│   ├── refinement/                # LLM-агент рефакторинга
│   └── report/                    # Генерация findings.json
├── tests/                         # Тесты
│   ├── unit/                      # Unit-тесты
│   ├── integration/               # Интеграционные тесты
│   └── contract/                  # Contract-тесты (protocol implementations)
├── resources/                     # Правила, промпты
│   └── rules/graph_rules.yaml     # Externalized Cypher-правила
└── profiles/                      # Примеры профилей async-profiler
```

---

## 🔧 Установка и настройка

### Быстрая установка

```bash
# Клонирование
git clone https://github.com/khoshov/burn-job.git
cd burn-job

# Установка зависимостей (рекомендуется через uv)
uv venv
uv pip install -e ".[test]"

# Или через pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

### Проверка установки

```bash
burn-job version
# Expected: Burn-Job CLI version 0.1.0

pytest tests/ -v
# Expected: 27 passed
```

### Предварительные требования для Java-проекта

Для полного цикла необходимо:

1. **Установить Java JDK 17+** и настроить `JAVA_HOME`:
   ```bash
   export JAVA_HOME=/path/to/jdk-17
   ```

2. **Установить Apache Maven**:
   ```bash
   mvn --version
   # Apache Maven 3.8+
   ```

3. **Скомпилировать целевое Java-приложение**:
   ```bash
   cd java
   mvn compile
   cd ..
   ```

4. **Профилирование** (async-profiler):
   ```bash
   # Скачать async-profiler: https://github.com/async-profiler/async-profiler
   # CPU sampling:
   java -agentpath:/path/to/libasyncProfiler.so=start,event=cpu,file=profile.collapsed,interval=7ms -jar app.jar

   # Allocation profiling:
   java -agentpath:/path/to/libasyncProfiler.so=start,event=alloc,file=profile_alloc.collapsed -jar app.jar
   ```

---

## 📝 Конфигурация окружения

### Переменные окружения

| Переменная | По умолчанию | Описание |
|-----------|-------------|---------|
| `BURN_JOB_DB_PATH` | `./profiler_graph.db` | Путь к файлу БД KùzuDB |
| `BURN_JOB_PROFILE_PATH` | `./app_profiling_full.collapsed` | Путь к collapsed-файлу профайлера |
| `BURN_JOB_LOG_PATH` | `./runlog/agent_run.log` | Путь к логу выполнения |
| `BURN_JOB_HOST` | `http://localhost:8080` | Хост целевого приложения |
| `BURN_JOB_CONCURRENCY` | `50` | Конкурентность нагрузочного теста |
| `BURN_JOB_DURATION_SEC` | `5` | Длительность нагрузочного теста (сек) |
| `BURN_JOB_MAX_ITERATIONS` | `3` | Макс. итераций LLM-рефакторинга |
| `BURN_JOB_MODEL` | `deepseek-coder` | Модель LLM для генерации кода |

### Структура файлов конфигурации

```yaml
# resources/rules/graph_rules.yaml — определяет Cypher-правила для детекторов
rules:
  - id: N_PLUS_ONE_QUERIES
    primary_taxonomy: T6
    category: DATABASE_QUERIES
    severity: HIGH
    edge: CALLS
    match:
      ...
```

---

## 🎯 Детекторы (T1–T9): подробное описание

### Общая архитектура детекции

Детекторы работают в **четыре этапа**, каждый из которых обогащает результат:

```
                    ┌──────────────────────────┐
                    │ 1. KuzuDB Graph Analyzers │ ◄─── graph_rules.yaml
                    │  (rule_engine.run())      │      (Cypher-запросы)
                    └────────────┬─────────────┘
                                │ graph_anomalies[]
                                │
                    ┌────────────▼─────────────┐
                    │ 2. Static AST Detectors   │ ◄─── patterns.py
                    │  (iter_method_bodies,     │      (прямой обход Java AST)
                    │   regex-паттерны)          │
                    └────────────┬─────────────┘
                                │ static_anomalies[]
                                │
                    ┌────────────▼─────────────┐
                    │ 3. _merge_dual_evidence() │ ◄─── Cross-reference по
                    │  (слияние по type+callee) │      type + method name
                    └────────────┬─────────────┘
                                │ merged[]
                                │  • _dual_evidence: True/False
                                │  • _approaches: ["graph","static"]
                                │  • evidence_detail: {graph: ..., static: ...}
                                │  • confidence: 0.5..0.95
                                │
                    ┌────────────▼─────────────┐
                                │ final[]
                                │  (sorted: dual-evidence first)
                                ▼
                         LLM Prompt / findings.json
```

**Ключевое новшество**: этап 3 — dual-evidence merge. Когда один и тот же тип дефекта найден и в графе БД, и в исходниках:

```python
# orchestrate.py:_merge_dual_evidence()
static_by_key[_method_identity(a)].append(a)   # static findings indexed
graph_by_key[_method_identity(a)].append(a)     # graph findings indexed

# Для каждого key, найденного обоими подходами:
if static_list and graph_list:
    finding["_dual_evidence"] = True
    finding["_approaches"] = ["graph", "static"]
    finding["evidence_detail"] = {
        "graph": {"sample_count": ..., "percentage": ...},
        "static": {"source_location": "File.java:42", "description": ...},
    }
    finding["confidence"] = 0.85  # повышенный confidence
```

### Сводная таблица способов обнаружения

| ID | Дефект | Graph DB | Static AST | Confidence |
|----|--------|:--------:|:----------:|:---------:|:----------:|
| **T1** | Redundant Operations | Cypher (r.percent > 0.4) | duplicate methods diff | 0.5–0.85 |
| **T2** | Inefficient Algorithms | Cypher (LINEAR_SEARCH) | nested loop depth ≥ 2 | 0.5–0.85 |
| **T3** | Improper Function Usage | Cypher (HEAVY_ENTITY_FETCH) | existence check full fetch | 0.5–0.85 |
| **T4** | Data Layout | Cypher (ARRAY_ALLOCATION) | object layout estimator | 0.5–0.7 |
| **T5** | Redundant Checks | Cypher + reachability | static call graph (javap) | 0.5–0.9 |
| **T6** | DB Queries | Cypher (N+1, save in loop) | N+1 lazy collection access | 0.5–0.85 |
| **T7** | Memory Leaks | Cypher (retained objects) | — | 0.5–0.8 |
| **T8** | Memory Bloat | Cypher (allocations) | — | 0.5–0.7 |
| **T9** | CPU Hotspots | Cypher (top-N by %) | — | 0.5–0.8 |

### Принцип работы каждого детектора

#### 1. T1: `Redundant Operations` (Избыточные операции)

**Источники:**
- **Graph DB**: `EXCESSIVE_STRING_CONCAT` правило — MATCH `()-[r:CALLS]->()` WHERE callee содержит `StringBuilder`/`String.concat` и `r.percent > 0.4`
- **Static**: `detect_duplicate_methods()` — сравнение нормализованных тел методов через `difflib.SequenceMatcher`, порог схожести 85%

**Cypher-запрос** (из `graph_rules.yaml`):
```cypher
MATCH ()-[all_r:CALLS]->()
WITH sum(all_r.count) AS totalSamples
MATCH (a:Method)-[r:CALLS]->(b:Method)
WHERE (b.className CONTAINS 'StringBuilder'
    OR (b.className CONTAINS 'String' AND b.methodName CONTAINS 'concat'))
  AND cast(r.count AS DOUBLE) / cast(totalSamples AS DOUBLE) * 100.0 > 0.4
RETURN a, b, r.count, r.count / totalSamples * 100 AS percent
```

#### 2. T2: `Inefficient Algorithms` (Алгоритмическая неэффективность)

**Источники:**
- **Graph DB**: `LINEAR_SEARCH_IN_LOOP` — MATCH callee class `List`/`ArrayList`/`LinkedList` + method `contains`/`indexOf`/`remove` + `r.percent > 0.04`. Есть `severity_override`: если percent ≤ 0.12 или caller содержит `SmallMatch` → severity понижается до LOW
- **Static**: `detect_nested_loops()` — поиск foreach-циклов, где итерабельное выражение внутреннего цикла зависит от переменной внешнего

#### 3. T3: `Improper Function Usage` (Некорректное использование функций)

**Источники:**
- **Graph DB**: `HEAVY_ENTITY_FETCH` — MATCH Method с class, содержащим `AttributeConverter`/`Converter`/`TypeDescriptor`/`PersistenceContext`, `percent > 0.4`
- **Graph DB**: `FULL_FETCH_FOR_EXISTENCE_CHECK` — caller содержит `exists`/`check`/`Count`, callee содержит `findAll`/`getEmployees`, `percent > 0.08`
- **Static**: `detect_existence_check_full_fetch()` — поиск присваиваний из Repository-методов, где все последующие использования — только null/empty/size checks

#### 4. T4: `Data Layout` (Неоптимальная упаковка данных)

**Источники:**
- **Graph DB**: `ARRAY_ALLOCATION_PRESSURE` — MATCH Method с class, содержащим `byte[]`/`Object[]`/`char[]`, `percent > 0.85`
- **Static**: `object_layout.py:compute_static_object_layout()` — анализ полей класса, вычисление `wasted_bytes` из-за неправильного порядка полей

#### 5. T5: `Redundant Checks` (Избыточные проверки)

**Источники:**
- **Graph DB**: Cypher-правила + статический call graph из `javap`
- **Static**: `callgraph.py:build_static_call_graph()` — декомпиляция `.class` файлов через `javap -v -c -p`, построение графа вызовов
- **Reachability**: `compute_reachable()` — BFS от entry points (Spring `@GetMapping`, `@PostMapping`, JUnit `@Test`, `main`) для определения dead code


#### 6. T6: `DB Queries` (Проблемы SQL-запросов)

**Источники:**
- **Graph DB**: `N_PLUS_ONE_QUERIES` — MATCH callee `findBy`/`getEmployees`/`PersistentBag`, `percent > 0.4`
- **Graph DB**: `SAVE_IN_LOOP_UNBATCHED` — MATCH callee `AbstractSaveEventListener.save`, `percent > 0.4`
- **Graph DB**: `CONNECTION_POOL_STARVATION` — MATCH callee `HikariPool.getConnection`, `percent > 0.25`
- **Static**: `detect_n_plus_one()` — поиск lazy `@OneToMany`/`@ManyToMany` getter'ов, вызываемых внутри цикла по результату Repository-запроса

#### 7. T7: `Memory Leaks` (Утечки памяти)

**Источники:**
- **Graph DB**: `UNBOUNDED_CACHE_OR_COLLECTION_GROWTH` — MATCH callee `Map`/`List`/`Cache`/`caffeine` + `put`/`add`/`get`, `percent > 0.08`
- **Differential**: Cross-run сравнение `RetainedObject.count` между baseline и candidate — если количество растёт → потенциальная утечка


#### 8. T8: `Memory Bloat` (Раздувание памяти)

**Источники:**
- **Graph DB**: `BOUNDED_REQUEST_COLLECTION` — caller содержит `processBoundedPage`/`BoundedPage`, считается non-defect если bounded
- **Differential**: `compare_runs()` для `Allocation.bytes` между профилями

#### 9. T9: `CPU Hotspots` (Горячие точки CPU)

**Источники:**
- **Graph DB**: `CPU_HOTSPOT_METHOD` — MATCH Method с class, начинающимся с `com.example`/`examples`, `percent > 0.85`, TOP 10 по `sampleCount DESC`
- **Graph DB**: `MICROBENCHMARK_REGEX_COMPILE` — MATCH callee `Pattern.compile`, `percent > 0.12`, exclude `Global` class


### Dual-evidence слияние

Функция `_merge_dual_evidence()` в `orchestrate.py` — ключевое звено, объединяющее результаты двух подходов:

```python
# Алгоритм слияния:
# 1. Индексируем static_anomalies и graph_anomalies по ключу "type|callee"
# 2. Для каждого ключа:
#    - Если есть в обоих → merged finding с _dual_evidence=True
#      + evidence_detail с данными из обоих источников
#      + confidence = 0.85 (или выше при cross-run diff)
#    - Если только в графе → _approaches=["graph"], confidence 0.7
#    - Если только в статике → _approaches=["static"], confidence 0.5
# 3. Сортируем: dual-evidence → graph-only → static-only
```

**Формат merged finding**:
```json
{
  "type": "N_PLUS_ONE_QUERIES",
  "severity": "HIGH",
  "caller": "com/example/Service.java:42",
  "callee": "com/example/Service.java:85",
  "_dual_evidence": true,
  "_approaches": ["graph", "static"],
  "confidence": 0.85,
  "evidence_detail": {
    "graph": {
      "sample_count": 127,
      "percentage": 1.2,
      "description": "Method triggers lazy collection initialization (127 samples)"
    },
    "static": {
      "source_location": "Service.java:85",
      "description": "Iterates repository result and calls lazy getter 'getDepartments()' inside loop"
    }
  },
  "description": "[Dual evidence: graph + static] Iterates repository result... (confirmed by profiling: 127 samples, 1.2%)"
}
```
---

## 🔧 Варианты исправлений (Fix Variants)

Для каждого типа дефекта система предлагает один или несколько вариантов исправления. Все варианты генерируются через LLM. Подробнее о механизме выбора победителя см. в разделе "8-этапный цикл автономной оптимизации".

### Таблица всех fix вариантов

| Дефект (type) | T | LLM Variant 1 | LLM Variant 2 | LLM Variant 3 |
|---|---|---|---|---|
| N_PLUS_ONE_QUERIES | T6 | JOIN FETCH JPQL | @EntityGraph | DTO Projection | | SAVE_IN_LOOP_UNBATCHED | T6 | saveAll с JDBC batching | --- | --- |
| FULL_FETCH_FOR_EXISTENCE_CHECK | T3 | COUNT query repository.existsBy() | --- | --- |
| HEAVY_ENTITY_FETCH | T3 | Interface Projection | --- | --- |
| IN_MEMORY_FILTERING | T8 | PageRequest | Slice (без COUNT) | --- |
| LINEAR_SEARCH_IN_LOOP | T2 | Set lookup | HashMap index | --- |
| QUADRATIC_NESTED_LOOP | T2 | Precompute Map index | Sort + linear pass | --- |
| EXCESSIVE_STRING_CONCAT | T1 | StringBuilder | String.format | --- |
| DUPLICATE_METHOD_BODY | T1 | Extract method | Strategy pattern | --- |
| DEAD_OR_UNREACHABLE_CODE | T5 | Remove dead code | Add entry point | --- |
| UNBOUNDED_CACHE_GROWTH | T7 | LRU LinkedHashMap | Caffeine maxSize | --- |
| RETAINED_OBJECT_ACCUMULATION | T7 | WeakReference | Eviction policy | --- |
| CONNECTION_POOL_STARVATION | T6 | Increase pool size | Reduce hold time | --- |
| CPU_HOTSPOT_METHOD | T9 | Algorithmic change | Loop optimization | | MICROBENCHMARK_REGEX_COMPILE | T9 | Static Pattern field | --- | --- |
| EXCESSIVE_STRING_ALLOCATIONS | T8 | StringBuilder reuse | Collectors.joining() | --- |
| BOXED_WRAPPER_OVERHEAD | T4 | Primitive collections (fastutil) | Primitive IntStream | --- |
| ARRAY_ALLOCATION_PRESSURE | T4 | Pre-size buffer | ThreadLocal pool | --- |
| THREAD_LOCK_CONTENTION | T8 | ReadWriteLock | ConcurrentHashMap/Atomic | --- |
| DUPLICATE_LAYER_VALIDATION | T5 | Consolidate validation | --- | --- |

### Примеры LLM-генерированных вариантов

**N+1 Queries** -- три варианта исправления:

```java
// VARIANT 1: JOIN FETCH JPQL
@Query("SELECT d FROM Department d JOIN FETCH d.employees")
List<Department> findAllWithEmployees();

// VARIANT 2: @EntityGraph
@EntityGraph(attributePaths = "employees")
@Query("SELECT d FROM Department d")
List<Department> findAllEntityGraph();

// VARIANT 3: DTO Projection
public interface DepartmentSummary {
    Long getId();
    String getName();
    List<EmployeeSummary> getEmployees();
}
public interface EmployeeSummary {
    Long getId();
    String getEmail();
}
```

**In-Memory Filtering** -- два варианта:

```java
// VARIANT 1: PageRequest (полноценная пагинация с COUNT)
return repository.findByStatusOptimal(status,
    PageRequest.of(page, size)).getContent();

// VARIANT 2: Slice (без COUNT запроса, только LIMIT+OFFSET)
return repository.findSliceByStatus(status,
    PageRequest.of(page, size)).getContent();
```

**Full Entity Fetch** -- проекция вместо полной сущности:

```java
// Вместо: List<Employee> employees = repository.findAll();
// VARIANT 1: Interface Projection
public interface EmployeeView {
    Long getId();
    String getFirstName();
    String getLastName();
    String getEmail();
}
List<EmployeeView> findAllProjectedBy();
```

### Процесс выбора варианта

**Single LLM mode** (с API key): LLM генерирует один вариант, оптимальный под контекст. Использует `generator_prompt.jinja2` с findings, complexity-анализом и evaluator feedback.
3. **Multi-Variant mode** (--multi-variant): LLM генерирует 3 варианта. Каждый проходит `mvn test-compile` и бенчмаркается. Выбирается лучший по score.
4. **JFR evaluation** (--enable-jfr): к бенчмарку добавляется JFR-профилирование (CPU samples от jcmd) для точного сравнения вариантов.

---

## 📐 Правила `graph_rules.yaml`

Все Cypher-правила вынесены в `resources/rules/graph_rules.yaml`. Это позволяет изменять пороги и добавлять новые правила без изменения кода Python.

**Структура правила**:
```yaml
- id: N_PLUS_ONE_QUERIES          # Уникальный ID типа дефекта
  primary_taxonomy: T6            # Основная таксономия
  also_relevant_to: [T2]          # Дополнительные категории
  category: DATABASE_QUERIES      # Категория для отчёта
  severity: HIGH                  # Базовая серьёзность
  edge: CALLS                     # Тип: CALLS (ребро) или Method (узел)
  match:                          # Условия срабатывания (AND)
    any:                          #   OR-of-ANDs
      - callee_method_contains: [findBy, getEmployees]
      - callee_class_contains: [PersistentBag]
  exclude:                        # Исключения (необязательно)
    caller_class_equals: [TestConfig]
  threshold:                      # Порог срабатывания
    field: percent                #   percent или count
    op: ">"                       #   >, >=, <, <=, ==
    value: 0.4                    #   значение
  severity_override:              # Понижение severity (необязательно)
    low_if_percent_lte: 0.12
    low_if_caller_contains: [SmallMatch]
  description_template:           # Шаблон описания
    "Method '{caller}' triggers lazy collection... ({count} samples)"
```

**Типы правил**:
- `edge: CALLS` → `MATCH (a:Method)-[r:CALLS]->(b:Method) WHERE ...`
- `node_type: Method` → `MATCH (m:Method) WHERE ...` (для одиночных узлов)

**Поддерживаемые поля match**:
- `caller_class_contains`, `caller_class_equals`, `caller_method_contains`, `caller_method_equals`
- `callee_class_contains`, `callee_class_equals`, `callee_method_contains`, `callee_method_equals`
- `class_contains`, `class_equals`, `class_starts_with` (для node_type)

**Текущие правила** (19 штук):
SAVE_IN_LOOP_UNBATCHED, EXCESSIVE_STRING_CONCAT, LINEAR_SEARCH_IN_LOOP, HEAVY_ENTITY_FETCH, FULL_FETCH_FOR_EXISTENCE_CHECK, N_PLUS_ONE_QUERIES, CONNECTION_POOL_STARVATION, ARRAY_ALLOCATION_PRESSURE, UNBOUNDED_CACHE_OR_COLLECTION_GROWTH, BOUNDED_REQUEST_COLLECTION, CPU_HOTSPOT_METHOD, MICROBENCHMARK_REGEX_COMPILE, и другие.

---

## 🔄 8-Этапный цикл автономной оптимизации

```
  ⚙️                  ⚙️                  ⚙️                  ⚙️
  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
  │  1. Сканирование│ ──► │  2. Генерация  │ ──► │ 3. Исполнение  │ ──► │   4. Инжест    │
  │   контроллеров  │     │ нагруз. тестов  │     │ нагруз. тестов │     │ трейсов в Kùzu │
  └────────────────┘     └────────────────┘     └────────────────┘     └───────┬────────┘
                                                                                │
  ⚙️                  ⚙️                  🤖                                 │
  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐             │
  │  8. Выбор      │ ◄── │   7. Maven     │ ◄── │  6. LLM Цикл   │ ◄──────────┘
  │   победителя   │     │  верификация   │     │  рефакторинга  │ ◄── 5. Детекция
  └────────────────┘     └────────────────┘     └────────────────┘
                                                    ⚙️
```

**Легенда**: ⚙️ = rule-based (без LLM)  |  🤖 = использует LLM

**Детальное описание каждого этапа:**

### Этап 1: Сканирование эндпоинтов ⚙️
- `ControllerScanner.scan_directory()` обходит `java/src/main/java`
- Ищет `@RestController`, `@Controller`, `@GetMapping`, `@PostMapping` и т.д.
- Результат: `List[EndpointInfo]` — path, HTTP method, controller class, method name
- **LLM не используется** — чистое regex-сканирование Java-исходников

### Этап 2: Генерация нагрузочного теста ⚙️
- `LoadtestGenerator.generate_script()` создаёт Python-скрипт
- Использует `ThreadPoolExecutor` для многопоточной отправки запросов
- Скрипт сохраняется в `loadtest/api_loadtest_suite.py`
- **LLM не используется** — шаблонный генератор кода

### Этап 3: Исполнение нагрузочного теста ⚙️
- Запускает сгенерированный скрипт через `subprocess.run()`
- Конкурентность и длительность из `Config` (переменные окружения)
- **LLM не используется** — механический запуск subprocess

### Этап 4: Инжест трейсов в KùzuDB ⚙️
- `KuzuGraphStore.ingest_profile()` парсит `.collapsed` файл async-profiler
- Формат: `frame1;frame2;...;frameN count`
- Создаёт узлы `Method` и рёбра `CALLS` с весом `count`
- Инициализирует схему: `Method`, `SqlStatement`, `Issue`, `CALLS`, `EXECUTES`, `HAS_DEFECT`
- **LLM не используется** — pure Python-парсинг + Cypher MERGE

### Этап 5: Детекция дефектов (T1–T9) — **центральный этап** ⚙️
- `analyze_anomalies()` в `orchestrate.py`
- 3 суб-этапа:
  1. **KuzuDB analyzers**: `rule_engine.run()` выполняет Cypher-запросы из `graph_rules.yaml` для T1–T9
  2. **Static AST detectors**: `patterns.py` обходит Java-файлы напрямую
  3. **`_merge_dual_evidence()`**: Cross-референс результатов (при обнаружении одного дефекта и в графе, и в статике)
- Результат: список anomaly-словарей с confidence, evidence_detail, _approaches
- **LLM не используется** — все детекторы rule-based, ни один не вызывает LLM API

### Этап 6: LLM-цикл рефакторинга 🤖

**Цель:** Для каждого найденного дефекта сгенерировать оптимизированный Java-код, проверить его компиляцию и применить улучшения.

**Центральный модуль:** `refinement/iterative_loop.py:run_iterative_loop()`

```
                 +---------------------------------------------+
                 |            findings.json (from Step 5)       |
                 |  [{file, mechanism, pdf_taxonomy, fix, ...}] |
                 +---------------------+-----------------------+
                                       |

                                       |
             +-------------------------v-----------------------+
             |             1-3 iterations of improvement       |
             |    +----------+   +----------+   +----------+   |
             |    |iteration |-->|iteration |-->|iteration |   |
             |    |    1     |   |    2     |   |    3     |   |
             |    +-----+----+   +----+-----+   +----+-----+   |
             |          |             |              |          |
             |          v             v              v          |
             |    +----------+  +----------+  +----------+      |
             |    |complexity|  |complexity|  |complexity|      |
             |    | analysis |  | analysis  |  | analysis |     |
             |    +----------+  +----------+  +----------+      |
             |          |             |              |          |
             |          v             v              v          |
             |    +----------+  +----------+  +----------+      |
             |    |  LLM    |  |  LLM    |  |  LLM    |     |
             |    |  refactor|  |  refactor |  |  refactor|     |
             |    +-----+----+  +-----+----+  +-----+----+     |
             |          |             |              |          |
             |          v             v              v          |
             |    +----------+  +----------+  +----------+      |
             |    |   mvn    |  |   mvn    |  |   mvn    |      |
             |    |test-comp.|  |test-comp.|  |test-comp.|      |
             |    +-----+----+  +-----+----+  +-----+----+     |
             |          |             |              |          |
             |     pass +--- retry ---+--- fail -----+          |
             |          |                        3 fails        |
             |          v                        -> rollback    |
             |    +----------+                                   |
             |    |  score   |<--+                               |
             |    |candidate |                                   |
             |    +----------+                                   |
             +--------------------------------------------------+
                                       |
                                       v
                             Refactored Java file
```

##### Два режима работы


**2. LLM mode** -- `refinement/agent.py:LLMAgent`

Генерация кода через OpenAI-compatible API:

1. **Системный промпт** (`agent.py:SYSTEM_PROMPT`): описывает правила -- сохранять API-контракты, не удалять поведение, output в ` ``` `java` `` ` блоках
2. **Промпт пользователя** (`generator_prompt.jinja2`): содержит исходный код, findings из findings.json, complexity-анализ, feedback от evaluator
3. **Извлечение кода** (`extract_code_block()`): из ответа LLM парсится блок ` ``` `java ... ` ``` `` `


Провайдеры: DeepSeek (по умолчанию), OpenAI, любой OpenAI-compatible endpoint.

**Настройка LLM:**

```bash
# DeepSeek (по умолчанию)
export DEEPSEEK_API_KEY=sk-...
export LLM_MODEL=deepseek-chat

# OpenAI
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o

# Кастомный endpoint
export LLM_API_KEY=...
export DEEPSEEK_BASE_URL=https://your-endpoint/v1
```

##### Multi-Variant режим (--multi-variant / --enable-jfr)

Вместо одного варианта LLM генерирует **3 различных кандидата**:

| Defect | VARIANT_1 | VARIANT_2 | VARIANT_3 |
|--------|-----------|-----------|-----------|
| N+1 Queries | JOIN FETCH JPQL | @EntityGraph | DTO Projection |
| In-Memory Filter | PageRequest | Slice (без COUNT) | -- |
| Save in Loop | saveAll batching | -- | -- |
| Full Entity Fetch | Interface Projection | -- | -- |

**Механизм выбора победителя** (`evaluator.py:evaluate_variant_candidates()`):

1. Применить каждый вариант к файлу
2. Проверить сборку (`mvn test-compile`) -- отсеять некомпилируемые
3. Забенчмаркать каждый прошедший вариант:
   - `avg_latency_ms` -- средняя задержка endpoint
   - `avg_sql_count` -- количество SQL-запросов (из X-Sql-Count header)
   - `success_rate` -- процент успешных запросов
4. **JFR профилирование** (опционально, `--enable-jfr`):
   - `jcmd JFR.start` -> нагрузка -> `jcmd JFR.stop` -> парсинг .jfr -> `cpu_samples`
5. **Score** каждого варианта:

   ```python
   score = (1000 - avg_sql_count * 100) + (100 - avg_latency_ms) + (1000 - cpu_samples * 2)
   ```

6. **Победитель**: вариант с максимальным score
7. **Rollback**: если ни один не прошёл сборку -> восстановление исходного кода

##### Весь scoring pipeline

```text
                                 Scoring
                              (выбор победителя)
                                    |
         +--------------------------+--------------------------+
         |                          |                          |
         v                          v                          v
  Iterative loop score      Multi-Variant JFR score     Pipeline score
  (iterative_loop.py)       (evaluator.py)              (scorer.py)
         |                          |                          |
         v                          v                          v
  100 - AST penalties        1000 - sql*100             0.6 * deltaLat
                              + 100 - latency            + 0.3 * deltaRPS
                             + 1000 - cpu*2             + 0.1 * deltaGC
```

**Scoring внутри итеративного цикла** (`iterative_loop.py:score_candidate()`):

```python
def score_candidate(code, complexity_res):
    score = 100.0
    nesting = complexity_res["max_nesting_depth"]
    if nesting > 1:
        score -= 10.0 * (nesting - 1)   # -10 за каждый уровень вложенности > 1
    for issue in complexity_res["issues"]:
        if sev == "high":   score -= 15.0
        elif sev == "medium": score -= 5.0
    if num_loops >= 3:       score -= 5.0
    if suggestions:          score -= 3.0 * len(suggestions)
    return max(score, 0.0)
```

Оценка основана на AST-сложности (глубина вложенности, количество проблем, количество циклов). Это дешёвый способ отсечь заведомо некачественные варианты до Maven-верификации.

### Этап 7: Maven-верификация ⚙️
- `verify_compilation()` запускает `mvn test-compile` в директории `java/`
- Если сборка не удалась: +1 к счётчику consecutive_errors
- После **3 последовательных ошибок** -- `rolled_back_to_original` (восстановление исходного кода, завершение цикла)
- Успешная сборка: обнуление счётчика, фиксация текущего варианта в `current_code`
- **LLM не используется** -- стандартный вызов Maven CLI

### Этап 8: Оценка и выбор победителя ⚙️

Применяется на трёх уровнях:

| Уровень | Модуль | Что оценивает | Метод |
|---------|--------|---------------|-------|
| Iterative loop (внутренний) | `iterative_loop.py` | Качество кода после каждой итерации | AST-complexity score (0..100) |
| Multi-Variant JFR (параллельный) | `evaluator.py` | Производительность 3+ кандидатов | SQL count + Latency + CPU samples |
| Pipeline (финальный) | `scorer.py` | Общий прирост после всех исправлений | `0.6*dLat + 0.3*dRPS + 0.1*dGC` |

**Pipeline Score** (`pipeline/scorer.py:Scorer.evaluate()`):

```python
Score = 0.6 * deltaLatency_p95 + 0.3 * deltaRPS + 0.1 * deltaGC
```

- **deltaLatency_p95**: относительное изменение 95-го перцентиля задержки (нормализовано 0..1)
- **deltaRPS**: относительное изменение запросов в секунду
- **deltaGC**: относительное изменение GC allocations (из профайлера)

Веса конфигурируются в `core/config.py`: `WEIGHT_LATENCY_P95`, `WEIGHT_RPS`, `WEIGHT_GC_ALLOC`.

Итоговый выбор: лучший вариант применяется к файлу. Если все варианты не прошли -- файл возвращается к исходному состоянию.

### Итог: где LLM, а где нет### Итог: где LLM, а где нет

| Этап | Название | LLM? | Механизм |
|------|----------|:----:|----------|
| 1 | Сканирование контроллеров | ❌ | Regex по Java-файлам |
| 2 | Генерация нагрузочного теста | ❌ | Шаблонный Python-код |
| 3 | Исполнение нагрузочного теста | ❌ | subprocess |
| 4 | Инжест трейсов в KùzuDB | ❌ | Парсинг collapsed + Cypher |
| 5 | Детекция дефектов T1–T9 | ❌ | Cypher-запросы + AST regex |
| **6** | **LLM-цикл рефакторинга** | **✅** | **Jinja2-промпт → LLM → код** |
| 7 | Maven-верификация | ❌ | mvn test-compile |
| 8 | Оценка и выбор победителя | ❌ | Взвешенная сумма метрик |

**Весь пайплайн (8 этапов) включает только один LLM-вызов на этапе 6.** Детекция, инжест, верификация и оценка — полностью rule-based.

---

## 💻 Использование CLI

### Основные команды

```bash
# Справка
burn-job --help

# 1. Сканирование Spring эндпоинтов
burn-job scan --src ./java/src/main/java

# 2. Инжест профиля async-profiler в KùzuDB
burn-job ingest --profile ./app_profiling_full.collapsed --db ./profiler_graph.db

# 3. Запуск полного цикла авто-оптимизации
burn-job run-cycle --db ./profiler_graph.db --host http://localhost:8080

# 4. Версия
burn-job version
```

### Прямой запуск детекторов

```bash
# Все детекторы (T1–T9) + cross-reference
python -m burn_job.detectors.orchestrate \
  --db-path ./profiler_graph.db

# Только определённые категории
python -m burn_job.detectors.orchestrate \
  --db-path ./profiler_graph.db \
  --category T1,T2,T6

# Без cross-reference (отдельные списки graph и static)
python -m burn_job.detectors.orchestrate \
  --db-path ./profiler_graph.db \
  --no-cross-ref

# JSON-вывод
python -m burn_job.detectors.orchestrate \
  --db-path ./profiler_graph.db \
  --json

# LLM prompt-only
python -m burn_job.detectors.orchestrate \
  --db-path ./profiler_graph.db \
  --prompt-only

# С указанием classpath для статического call graph
python -m burn_job.detectors.orchestrate \
  --db-path ./profiler_graph.db \
  --classpath-dir ./java/target/classes
```

### Генерация findings.json

```bash
python -m burn_job.report.builder \
  --db-path ./profiler_graph.db \
  --output ./reports/sandbox/findings.json \
  --category T1,T2,T3,T6,T9
```

### Запуск отдельных анализаторов

```bash
# Статическая сложность кода
python -m burn_job.detectors.complexity --file ./java/src/main/java/com/example/Service.java

# Object layout анализ
python -m burn_job.detectors.object_layout ./java/src/main/java/com/example/Entity.java EntityName

# Дифференциальный анализ двух прогонов
python -m burn_job.detectors.differential \
  --db-path ./profiler_graph.db \
  --baseline-run-id run_1 \
  --candidate-run-id run_2

# Статический call graph
python -m burn_job.detectors.callgraph ./java/target/classes --json
```

---

## 📊 Scoring Function

Качество вариантов кода оценивается взвешенной суммой:

```python
Score = 0.6 * ΔLatency_p95 + 0.3 * ΔRPS + 0.1 * ΔGC
```

Где:
- **ΔLatency_p95** — относительное изменение 95-го перцентиля задержки (нормализованное, 0..1)
- **ΔRPS** — относительное изменение запросов в секунду (0..1)
- **ΔRPS** — относительное изменение GC allocations (0..1)

Веса конфигурируются в `core/config.py`: `WEIGHT_LATENCY_P95`, `WEIGHT_RPS`, `WEIGHT_GC_ALLOC`.

---

## 🧪 Запуск тестов

```bash
# Все тесты с покрытием
pytest

# Только unit-тесты
pytest tests/unit/

# Интеграционные + контрактные
pytest tests/integration/ tests/contract/

# С детальным отчётом по покрытию
pytest --cov=burn_job --cov-report=term-missing

# Без покрытия
pytest -v --no-header --cov=
```

### Структура тестов

| Директория | Тип | Что проверяет |
|-----------|-----|---------------|
| `tests/unit/` | Unit | Domain models, Core config, Detector protocol, Detector base, Rule engine, Graph store, Pipeline scanner, Scorer |
| `tests/integration/` | Integration | CLI commands, Domain context initialization, Graph store instantiation |
| `tests/contract/` | Contract | DetectorProtocol implementation, RuleEngine registration |

---

## 📄 Лицензия

Проект распространяется под лицензией MIT.
