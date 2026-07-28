# Burn Job — Performance Optimization Pipeline & Codebase Refactoring Engine

**Версия:** 0.1.0 | **Python:** >= 3.10 | **Лицензия:** MIT

Autonomous agentic pipeline for static bytecode analysis, dynamic profiler trace ingestion, and LLM-driven performance refactoring of Java applications.

---

## 📋 Описание проекта

**Burn Job** — это полностью автономная система анализа и оптимизации производительности Java-приложений (в первую очередь REST-сервисов на базе Spring Boot). Пайплайн комбинирует статический анализ байткода (`javap`) и AST исходного кода, динамический инжест вызовов из профайлера (async-profiler / JFR) во встраиваемую графовую БД **KùzuDB**, автоматическую генерацию нагрузочных скриптов и итеративный рефакторинг кода через LLM-агента.

---

## 🛠 Матрица зависимостей

### Python-библиотеки (`pyproject.toml`)

| Зависимость | Версия | Назначение / Роль |
|-------------|--------|-------------------|
| **`kuzu`** | `>= 0.3.0` | Встраиваемая графовая СУБД KùzuDB: хранение стектрейсов, узлов методов, графов вызовов (CALLS) и SQL-запросов |
| **`jinja2`** | `>= 3.0.0` | Шаблонизатор промптов для LLM-агента генерации оптимизированных вариантов кода |
| **`pytest`** *(test)* | `>= 8.0.0` | Основной фреймворк запуска unit, integration и contract тестов |
| **`pytest-cov`** *(test)* | `>= 5.0.0` | Сборщик покрытия кода тестами (`--cov=burn_job`) |

### Системное окружение и внешние инструменты

| Инструмент | Минимальная версия | Назначение |
|------------|-------------------|------------|
| **Python** | `>= 3.10` | Основной язык оркестрации и аналитических модулей |
| **Java JDK** | `>= 17` | Среда компиляции и выполнения целевого Java-приложения |
| **Apache Maven** | `>= 3.8` | Автоматическая компиляция (`mvn test-compile`) и верификация вариантов кода |
| **async-profiler / JFR** | `>= 2.9` | Профилирование CPU, выделения памяти (GC allocations) и блокировок потоков в формате `.collapsed` / `.jfr` |

---

## 🏛 Модульная архитектура пакета (`burn_job`)

Архитектура распределена по **6 строго изолированным доменным суб-пакетам** с однонаправленным потоком зависимостей:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                            burn_job.cli                                  │
│                 (Параметры CLI, совместимость флагов)                     │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│                          burn_job.pipeline                               │
│  (AutonomousOrchestrator, ControllerScanner, LoadtestGen, Scorer)         │
└──────────────────┬──────────────────────────────────────┬────────────────┘
                   │                                      │
┌──────────────────▼──────────────────┐ ┌─────────────────▼────────────────┐
│         burn_job.detectors          │ │         burn_job.graph           │
│ (RuleEngine, BaseDetector, T1–T9)   │ │  (KuzuGraphStore, TraceIngestor) │
└──────────────────┬──────────────────┘ └─────────────────┬────────────────┘
                   │                                      │
                   └──────────────────┬───────────────────┘
                                      │
┌─────────────────────────────────────▼────────────────────────────────────┐
│                           burn_job.domain                                │
│       (Finding, EndpointInfo, Metric, CodeVariant, PipelineContext)      │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│                            burn_job.core                                 │
│          (Config, Exceptions, Structured Logger, typing.Protocols)       │
└──────────────────────────────────────────────────────────────────────────┘
```

### Подробный обзор суб-пакетов

#### 1. `burn_job.core`
Ядро инфраструктуры и базовые примитивы системы:
- [config.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/core/config.py) — Централизованные настройки с поддержкой переменных окружения (`BURN_JOB_DB_PATH`, `BURN_JOB_HOST`, `BURN_JOB_CONCURRENCY`).
- [exceptions.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/core/exceptions.py) — Иерархия исключений (`BurnJobError`, `GraphStoreError`, `DetectorExecutionError`, `PipelineExecutionError`).
- [logging.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/core/logging.py) — Конфигуратор структурированных логов с файловой и консольной трассировкой.
- [protocols.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/core/protocols.py) — Строгие интерфейсные контракты `typing.Protocol` (`DetectorProtocol`, `StoreProtocol`, `ReportBuilderProtocol`).

#### 2. `burn_job.domain`
Неизменяемые сущности доменной модели и DTOs:
- [finding.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/domain/finding.py) — Доменная модель найденного дефекта (`Finding`, `Severity`, `SourceLocation`, `Anomaly`).
- [endpoint.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/domain/endpoint.py) — Модель Spring REST эндпоинта (`EndpointInfo`).
- [metrics.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/domain/metrics.py) — Метрики профилирования (`Metric`, `MetricSource`, `LatencyStats`, `MicrometerMetrics`).
- [variant.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/domain/variant.py) — Варианты оптимизированного кода (`CodeVariant`, `ScoringResult`).
- [pipeline_context.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/domain/pipeline_context.py) — Контейнер общего состояния выполнения пайплайна (`PipelineContext`, `PipelineStatus`).

#### 3. `burn_job.detectors`
Движок обнаружения проблем производительности. Комбинирует статический анализ кода (AST/байткод) и динамический Cypher-анализ стектрейсов в KùzuDB.

#### 4. `burn_job.graph`
Модуль интеграции с встраиваемой графовой СУБД KùzuDB:
- [store.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/graph/store.py) — Клиент KùzuDB (`KuzuGraphStore`), инициализация Cypher-схемы (узлы `Method`, `SqlStatement`, `Issue`, связи `CALLS`, `EXECUTES`).
- [ingest.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/graph/ingest.py) — Парсер трейсов профайлера в стеки вызовов.

#### 5. `burn_job.pipeline`
Оркестратор 8-этапного цикла авто-оптимизации:
- [scanner.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/pipeline/scanner.py) — Сканер `@RestController` и `@GetMapping` аннотаций в Java AST.
- [loadtest.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/pipeline/loadtest.py) — Генератор автономных Python-скриптов нагрузочного тестирования.
- [scorer.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/pipeline/scorer.py) — Расчёт качества вариантов по формуле: `Score = 0.6 * ΔLatency_p95 + 0.3 * ΔRPS + 0.1 * ΔGC`.
- [orchestrator.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/pipeline/orchestrator.py) — `AutonomousOrchestrator` полного цикла.

#### 6. `burn_job.cli`
Единая точка входа для работы из командной строки:
- [cli.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/cli.py) — Диспетчер команд `scan`, `ingest`, `run-cycle`, `version` с выдачей предупреждений при вызове устаревших параметров.

---

## 🔍 Детализированный механизм работы детекторов (T1–T9)

Детекторы `burn-job` разделены по технологии обнаружения на **Статический анализ (Static AST / Bytecode `javap`)**, **Динамический анализ KùzuDB (Cypher графовые запросы)** и **Гибридный анализ**.

### Сводная таблица способов обнаружения

| Правило таксономии | Название дефекта | Метод обнаружения | Источник данных |
|-------------------|------------------|-------------------|-----------------|
| **T1 (RedundantOps)** | Избыточные вычисления в циклах | **Гибридный** (AST + KùzuDB Cypher) | Дерево AST + Граф вызовов KùzuDB |
| **T2 (InefficientAlgos)** | Алгоритмическая неэффективность $O(N^2)$ | **Гибридный** (AST + KùzuDB Cypher) | Глубина вложенности AST + Сэмплы CPU KùzuDB |
| **T3 (ImproperFuncUsage)** | Неоптимальные вызовы JDK API | **Статический** (AST / `javap` Bytecode) | Сигнатуры вызовов в Java AST и байткоде |
| **T4 (DataLayout)** | Раздувание объектов и фрагментация | **Статический** (`javap` Layout Inspection) | Байткод классов Java (`javap -v`) |
| **T5 (RedundantChecks)** | Полная выгрузка вместо фильтрации/COUNT | **Гибридный** (AST + KùzuDB SQL) | Вызовы JPA/Hibernate AST + Граф запросов KùzuDB |
| **T6 (DbQueries)** | N+1 проблема SQL-запросов | **Динамический KùzuDB** (Cypher) | Связи `(Method)-[:EXECUTES]->(SqlStatement)` в KùzuDB |
| **T7 (MemoryLeak)** | Утечки памяти (Unclosed / Monotonic) | **Динамический KùzuDB** (Profiler Allocations) | Трейсы async-profiler (Allocation Mode) в KùzuDB |
| **T8 (MemoryBloat)** | Массовые короткоживущие объекты | **Гибридный** (AST + KùzuDB Allocations) | Аллокации DTO/JSON в профайлере + AST создание объектов |
| **T9 (CpuHotspots)** | Горячие точки CPU (>15% self-time) | **Динамический KùzuDB** (Cypher) | Сэмплы CPU узлов `Method` в графе KùzuDB |

---

### Подробный принцип работы каждого анализатора

#### 1. `T1RedundantOpsDetector` (Избыточные операции)
- **Как работает:**
  1. **Статическая фаза (AST):** Поисковый алгоритм проходит по узлам циклов (`for`, `while`, `stream().forEach()`) и ищет вычисления инвариантов (например, `list.size()`, `Pattern.compile()`, повторные конкатенации строк, создающие однотипные объекты).
  2. **Динамическая фаза (KùzuDB):** Запрашивает Cypher-графом узлы методов `MATCH (m:Method) WHERE m.samples > threshold` с высокой частотой вызова внутри узлов-предков циклов.
  3. **Результат:** Сопоставляет точку вызова в коде с горячей вершиной графа вызовов.

#### 2. `T2InefficientAlgosDetector` (Алгоритмическая неэффективность)
- **Как работает:**
  1. **Статическая фаза:** Вычисляет глубину вложенности циклов (Nesting Depth >= 2) и выявляет вызовы с линейной сложностью внутри циклов (например, `list.contains()` или `list.indexOf()` внутри `for`).
  2. **Динамическая фаза:** Анализирует Cypher-запросом квадратичный рост сэмплов профайлера при увеличении объема входных данных (`MATCH (m:Method) WHERE m.total_time_pct > 20.0`).

#### 3. `T3ImproperFuncUsageDetector` (Некорректное использование функций)
- **Как работает:**
  1. **Полностью статический анализ:** Анализирует AST и байткод `javap`.
  2. Детектирует паттерны:
     - Использование `String.replaceAll()` вместо `String.replace()` или кэшированного `Pattern.compile()`.
     - Автоупаковку/распаковку (Autoboxing `Integer` ↔ `int`) в примитивных стримах (`Stream<Integer>` вместо `IntStream`).
     - Создание промежуточных коллекций `Collectors.toList()` с последующим мгновенным вызовом `.get(0)` или `.size()`.

#### 4. `T4DataLayoutDetector` (Неоптимальная упаковка данных)
- **Как работает:**
  1. **Статический анализ байткода (`javap`):** Инспектирует структуру полей классов Java DTO и Entity.
  2. Вычисляет байтовое выравнивание и выявляет неупакованные примитивы (например, чередование `boolean`, `long`, `int`, выравниваемое JVM до дополнительных 8–16 байт на объект).
  3. Находит лишние поля-обёртки `java.lang.Boolean` / `java.lang.Long` вместо примитивов.

#### 5. `T5RedundantChecksDetector` (Избыточные проверки)
- **Как работает:**
  1. **Гибридный подход:**
  2. **AST:** Выявляет антипаттерн `repository.findAll().stream().filter(...)` или `repository.findAll().isEmpty()`.
  3. **KùzuDB:** Выполняет Cypher-запрос к узлам SQL-запросов `MATCH (m:Method)-[:EXECUTES]->(s:SqlStatement) WHERE s.text CONTAINS 'SELECT' AND NOT s.text CONTAINS 'COUNT' AND NOT s.text CONTAINS 'LIMIT'`.

#### 6. `T6DbQueriesDetector` (N+1 Запросы к БД)
- **Как работает:**
  1. **Динамический анализ графа KùzuDB:**
  2. Инжестирует SQL-логи трассировки ORM/Hibernate.
  3. Выполняет Cypher-запрос:
     ```cypher
     MATCH (e:Endpoint)-[:CALLS*]->(m:Method)-[:EXECUTES]->(s:SqlStatement)
     WITH e, s.pattern AS query_pattern, COUNT(s) AS exec_count
     WHERE exec_count > 10
     RETURN e.path, query_pattern, exec_count
     ```
  4. Фиксирует генерацию множественных однотипных SQL SELECT-запросов в пределах одного HTTP-запроса.

#### 7. `T7MemoryLeakDetector` (Утечки памяти)
- **Как работает:**
  1. **Динамический анализ профайлера (Allocation Mode):**
  2. Сравнивает несколько заходов нагрузочного теста в KùzuDB (`MATCH (m:Method) WHERE m.allocation_bytes_retained > threshold`).
  3. Выявляет незакрытые ресурсы (`AutoCloseable`, `InputStream`, `Connection`), статичные коллекции `static List/Map`, растущие без ограничения размера, и нечищенные `ThreadLocal` переменные.

#### 8. `T8MemoryBloatDetector` (Раздувание памяти / GC Pressure)
- **Как работает:**
  1. **Гибридный подход:**
  2. **Profiler:** Идентифицирует методы с наибольшим выделением памяти в секунду (`allocations/sec` > 500 MB/s).
  3. **AST:** Находит генерацию гигантских промежуточных JSON-дерева/DTO или создание буферов строки огромного размера без предварительного указания емкости `StringBuilder(capacity)`.

#### 9. `T9CpuHotspotsDetector` (Горячие точки CPU)
- **Как работает:**
  1. **Динамический анализ Cypher KùzuDB:**
  2. Выполняет агрегационный Cypher-запрос по графу вызовов:
     ```cypher
     MATCH (m:Method)
     WHERE m.self_cpu_samples / m.total_cpu_samples > 0.15
     RETURN m.class_name, m.method_name, m.self_cpu_samples
     ```
  3. Локализует методы, съедающие более 15% чистого процессорного времени (Self CPU Time).

---

## 🔄 8-Этапный цикл автономной оптимизации

```text
  ┌────────────────┐      ┌────────────────┐      ┌────────────────┐      ┌────────────────┐
  │  1. Сканирование│ ───► │  2. Генерация  │ ───► │ 3. Исполнение  │ ───► │   4. Инжест    │
  │   контроллеров │      │ нагруз. тестов │      │ нагруз. тестов │      │ трейсов в Kùzu │
  └────────────────┘      └────────────────┘      └────────────────┘      └───────┬────────┘
                                                                                  │
  ┌────────────────┐      ┌────────────────┐      ┌────────────────┐              │
  │  8. Выбор      │ ◄─── │   7. Maven     │ ◄─── │  6. LLM Цикл   │ ◄────────────┘
  │   победителя   │      │  верификация   │      │  рефакторинга  │ ◄─── 5. Детекция дефектов (T1-T9)
  └────────────────┘      └────────────────┘      └────────────────┘
```

1. **Сканирование эндпоинтов**: Извлечение всех Spring REST путей, HTTP-методов и параметров.
2. **Генерация нагрузки**: Создание многопоточного скрипта нагрузочного тестирования.
3. **Запуск нагрузки**: Прогрев и подача целевого RPS на приложение.
4. **Графовый инжест**: Преобразование стектрейсов async-profiler в граф узлов методов в KùzuDB.
5. **Поиск аномалий**: Выполнение Cypher-запросов и запуск правил таксономии T1–T9.
6. **LLM-рефакторинг**: Генерация оптимизированного Java-кода для каждого дефекта.
7. **Верификация сборки**: Проверка компилируемости изменённого кода через `mvn test-compile`.
8. **Оценка и выбор победителя**: Оценка прироста производительности и сохранение победившего варианта.

---

## 🚀 Быстрый старт и установка

### Установка в режиме разработки

```bash
# Клонирование репозитория
git clone https://github.com/khoshov/burn-job.git
cd burn-job

# Установка зависимостей и пакета в editable-режиме
pip install -e ".[test]"

# Или через uv (рекомендуется)
uv pip install -e ".[test]"
```

---

## 💻 Использование CLI

```bash
# 1. Сканирование эндпоинтов Java-проекта
burn-job scan --src ./java/src/main/java

# 2. Инжест сэмпла профайлера в KùzuDB
burn-job ingest --profile ./app_profiling_full.collapsed --db ./profiler_graph.db

# 3. Запуск полного 8-этапного автономного цикла
burn-job run-cycle --db ./profiler_graph.db --host http://localhost:8080

# 4. Проверка версии CLI
burn-job version
```

---

## 🧪 Запуск тестов (`pytest`)

Тестовая сюита построена на базе **`pytest`** и **`pytest-cov`**:

```bash
# Запуск всех тестов с генерацией отчета о покрытии
pytest

# Запуск только юнитов
pytest tests/unit/

# Запуск интеграционных и контрактных тестов
pytest tests/integration/ tests/contract/

# Запуск с детальным отчетом по незакрытым строкам
pytest --cov=burn_job --cov-report=term-missing
```

---

## 📄 Лицензия

Проект распространяется под лицензией MIT.
