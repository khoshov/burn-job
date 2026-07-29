---
name: burn-job-performance-refactor
description: Skill for automated static & dynamic profiling analysis, taxonomy defect detection (T1-T9), graph-based dependency querying via KuzuDB, and LLM-guided performance refactoring for Java Spring Boot services.
---

# Burn Job — Performance Refactoring Skill

Подключаемый артефакт (skill / workflow), расширяющий агента возможностью
анализировать Java Spring Boot проект, находить неоптимальный код и
предлагать (или сразу применять) исправления с измеренным приростом
производительности.

Точка входа — уже готовый Python-пакет `src/burn_job/`, установленный как
CLI-команда `burn-job` (см. `RUN.md` в корне репозитория за инструкцией по
установке из нуля). Этот каталог не дублирует код детекторов — он лишь
описывает возможности артефакта и то, как агент должен его вызывать.

## Возможности

1. **Сканирование контроллеров**: находит `@RestController`/`@GetMapping`/
   `@PostMapping` и т.д. в Java-исходниках, извлекает HTTP-маршруты.
2. **Инжест динамических трейсов**: парсит `.collapsed` (async-profiler) и
   `.jfr` (JFR) файлы в граф вызовов во встраиваемой KùzuDB.
3. **Таксономия дефектов T1–T9** (Cypher-правила по графу + статический
   AST-анализ, см. `README.md` раздел «Детекторы»):
   - **T1** — избыточные операции и повторные вычисления
   - **T2** — неэффективные алгоритмы (квадратичная сложность)
   - **T3** — некорректное использование функций (полная сущность вместо факта существования)
   - **T4** — ошибки в раскладке данных / memory overhead
   - **T5** — избыточные проверки и мёртвый код
   - **T6** — проблемы SQL-запросов (N+1, лишние round-trip)
   - **T7** — утечки памяти
   - **T8** — перерасход памяти
   - **T9** — избыточная нагрузка на CPU
4. **LLM-цикл рефакторинга**: генерирует 1–3 варианта исправления на дефект,
   компилирует (`mvn test-compile`), бенчмаркает через Micrometer/JFR,
   выбирает победителя по измеренной latency/SQL-count/CPU.
5. **Отчётность по схеме `SUBMISSION.md`**: `reports/sandbox/findings.json`
   (машиночитаемо, поля `family`/`pdf_taxonomy`/`mechanism`/`evidence`) и
   `reports/sandbox/report.md` (человекочитаемо).

## Как вызывать

```bash
# Только rule-based детекция, без LLM/бенчмарков (быстрая проверка)
burn-job detect --src <путь-к-java-src> --db ./profiler_graph.db

# Полный 8-этапный цикл с реальным бенчмаркингом и LLM-фиксами
burn-job run-cycle --src <путь-к-java-src> --variant-llm deepseek --apply

# Отдельные шаги пайплайна
burn-job scan --src <путь-к-java-src>
burn-job ingest --profile <profile.collapsed|profile.jfr> --db ./profiler_graph.db
burn-job jfr2collapsed <profile.jfr>
burn-job profile --pid <PID> --duration 30 --output ./app.jfr
burn-job llm-server --model-path <gguf>   # persistent локальный LLM backend
burn-job version
```

Полное описание команд, переменных окружения и архитектуры — в `README.md`
корня репозитория. Инструкция по установке зависимостей и запуску с нуля —
в `RUN.md`.
