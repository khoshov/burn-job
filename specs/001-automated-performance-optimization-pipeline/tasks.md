# Tasks: Автоматизированный контур профилирования, анализа и авто-исправления производительности Java бэкенда

**Input**: Design documents from `specs/001-automated-performance-optimization-pipeline/` (`spec.md`, `plan.md`)

---

## Phase 1: Setup & Infrastructure

- [ ] T001 Настройка Python-окружения (`kuzu`, `urllib`, `requests`) в `requirements.txt`
- [ ] T002 [P] Проверка конфигурации Spring Boot Actuator и подключения `ap-loader` (async-profiler) в `pom.xml`

---

## Phase 2: Foundational Infrastructure

- [ ] T003 Создание базовой графовой схемы KùzuDB (`Method`, `Class`, `SqlStatement`, `Issue`, `CALLS`, `EXECUTES`) в `skill/scripts/jfr_to_graph.py`
- [ ] T004 [P] Реализация вызова REST API профилирования (`POST /api/profiler/profile?duration=X`) в `loadtest/run_loadtest.sh`

---

## Phase 3: User Story 1 - Динамические API-тесты и сбор метрик/профилей (Priority: P1) 🎯 MVP

**Goal**: Динамическое сканирование `@RestController` контроллеров, исполнение API нагрузочного теста и сохранние отчетов Micrometer + `async-profiler` `.collapsed` профилей.

**Independent Test**: Запуск `python3 skill/scripts/generate_api_loadtests.py && python3 loadtest/api_loadtest_suite.py` приводит к успешной генерации `micrometer_report.json` и `app_profiling_full.collapsed`.

- [ ] T005 [P] [US1] Реализация динамического сканирования контроллеров Java в `skill/scripts/generate_api_loadtests.py`
- [ ] T006 [US1] Обновление `loadtest/api_loadtest_suite.py` для генерации HTTP запросов под параметр `?variant=vN`
- [ ] T007 [US1] Интеграция сбора метрик Micrometer в `loadtest/api_loadtest_suite.py`

---

## Phase 4: User Story 2 - Детекция проблем и графовая БД (KùzuDB) (Priority: P1)

**Goal**: Парсинг `.collapsed`/JFR профилей, построение графа вызовов и квалификация дефектов таксономии T1–T9 в KùzuDB.

**Independent Test**: `python3 skill/scripts/jfr_to_graph.py --input app_profiling_full.collapsed --db profiler_graph.db` возвращает найденные дефекты (N+1, In-Memory Filter, Save in Loop, Entity Fetch) с Cypher-ссылками.

- [ ] T008 [P] [US2] Парсинг `.collapsed` стектрейсов и формирование узлов/ребер KùzuDB в `skill/scripts/jfr_to_graph.py`
- [ ] T009 [US2] Реализация правил детекции таксономии T1-T9 в `skill/scripts/static_pattern_detectors.py`
- [ ] T010 [US2] Запись обнаруженных узлов `Issue` и связей `(Method)-[:HAS_DEFECT]->(Issue)` в `profiler_graph.db`

---

## Phase 5: User Story 3 - LLM Оптимизатор кода (Priority: P1)

**Goal**: Получение отчета из KùzuDB, отправка контекста проблемы в LLM-агент (`llm_agent.py`) и создание вариантов исправления на Java 21 с поддержкой Feature Toggles.

**Independent Test**: Запуск `python3 skill/scripts/llm_agent.py --report reports/sandbox/findings.json` создает сгенерированные вариантные файлы `*_FixedByAgent.java`.

- [ ] T011 [P] [US3] Форматирование системных и пользовательских промптов LLM с графовым контекстом в `skill/scripts/prompts/`
- [ ] T012 [US3] Реализация LLM-агента генерации кода в `skill/scripts/llm_agent.py` (DeepSeek / OpenAI / Offline fallback)
- [ ] T013 [US3] Поддержка компиляционной проверки вариантов (`mvn test-compile`) в `skill/scripts/llm_agent.py`

---

## Phase 6: User Story 4 - Итеративный бенчмарк в памяти и Scoring (Priority: P2)

**Goal**: Многократное тестирование вариантов в памяти без перезапуска JVM через `?variant=v1|v2|good` и ранжирование по формуле Scoring Function.

**Independent Test**: `python3 skill/scripts/benchmark_variants.py` выводит таблицу с дельтами Latency p95, RPS, GC allocations и значением $\text{Score}$.

- [ ] T014 [P] [US4] Настройка итеративного вызова нагрузочных сценариев под разные варианты в `skill/scripts/benchmark_variants.py`
- [ ] T015 [US4] Вычисление формулы $0.6 \Delta\text{Latency}_{p95} + 0.3 \Delta\text{RPS} + 0.1 \Delta\text{GC}$ в `skill/scripts/evaluate_variants_via_kuzu.py`
- [ ] T016 [US4] Выбор варианта $V_{\text{winner}}$ с максимальным положительным баллом.

---

## Phase 7: User Story 5 - Финализация в исходниках и Regression Gate (Priority: P2)

**Goal**: Полная автономия — физическое подставление сгенерированного Winner-кода в исходные Java-файлы и проверка `mvn test`.

**Independent Test**: Запуск `python3 skill/scripts/run_full_autonomous_cycle.py` приводит к обновлению Java файлов в `src/main/java` и зелёному прогону `mvn test`.

- [ ] T017 [US5] Атомарная перезапись исходных файлов Java выбранным Winner-кодом в `skill/scripts/run_full_autonomous_cycle.py`
- [ ] T018 [US5] Запуск интеграционных тестов `mvn test` и проверка сохранения функциональной корректности.

---

## Phase 8: Polish & Verification

- [ ] T019 Интеграционная валидация сквозного контура через `python3 skill/scripts/verify_full_pipeline.py`
- [ ] T020 Генерация итогового сравнительного отчета в `reports/EXECUTABLE_EVALUATION_REPORT.md`
