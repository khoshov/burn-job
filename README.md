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
Движок обнаружения проблем производительности:
- [base.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/detectors/base.py) — Абстрактный базовый класс `BaseDetector`, реализующий `DetectorProtocol`.
- [rule_engine.py](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/detectors/rule_engine.py) — Движок регистрации и параллельного запуска детекторов.
- [taxonomy/](file:///Users/stanislavkhoshov/Documents/burn-job/src/burn_job/detectors/taxonomy) — 9 классификаторов дефектов (T1–T9):
  - **T1**: Избыточные вычисления и операции в циклах
  - **T2**: Неэффективные алгоритмы и структуры данных
  - **T3**: Некорректное использование библиотечных функций
  - **T4**: Неоптимальное размещение объектов в памяти
  - **T5**: Избыточные проверки (Full Fetch vs existence check)
  - **T6**: N+1 и неоптимальные БД-запросы
  - **T7**: Утечки памяти (Memory Leaks)
  - **T8**: Раздувание памяти (Memory Bloat)
  - **T9**: Горячие точки CPU (CPU Hotspots)

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
