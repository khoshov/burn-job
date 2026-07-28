# 📊 Python Profiler & Graph Anomaly Analyzer

Набор инструментов на Python для преобразования профилей выполнения Java-приложения (`async-profiler`, `.collapsed`, `.jfr`) в графовую модель данных **KùzuDB** («SQLite для графов») и автоматического выявления антипаттернов производительности по таксономии **T1–T9**.

---

## 🛠️ Состав скриптов

### Основные утилиты:
| Файл | Описание |
|---|---|
| **[jfr_to_graph.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/jfr_to_graph.py)** | Парсер профилей. Читает стеки вызовов (`.collapsed`, `.txt`) или бинарные `.jfr` файлы и строит граф вызовов в KùzuDB. |
| **[analyze_anomalies.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyze_anomalies.py)** | Главный оркестратор анализа. Запускает проверку по всем (или выбранным) категориям таксономии T1–T9. |
| **[compare_runs.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/compare_runs.py)** | Движок сравнения прогонов (Diff). Сравнивает два прогона профилирования (`--base-run` vs `--target-run`). |
| **[non_defects.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/non_defects.py)** | Модуль классификации дефектов (Правила раздела 7). Помечает паттерны, не являющиеся дефектами. |

### Модульные анализаторы таксономии (`scripts/analyzers/`):
| Модуль | Таксономия | Выявляемая проблема |
|---|---|---|
| **[t1_redundant_ops.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t1_redundant_ops.py)** | **T1** | Избыточные вычисления и операции (сохранения в цикле без batching, массовая конкатенация строк). |
| **[t2_inefficient_algos.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t2_inefficient_algos.py)** | **T2** | Неэффективные алгоритмы (поиск $O(N)$ в циклах через `List.contains`, $O(N^2)$ квадратичные вложенные циклы). |
| **[t3_improper_func_usage.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t3_improper_func_usage.py)** | **T3** | Неправильное использование функций (фетч полной сущности JPA / LOB вместо DTO-проекции или `exists`). |
| **[t4_data_layout.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t4_data_layout.py)** | **T4** | Ошибки в раскладке данных (перерасход памяти на объекты-обёртки `Integer`/`Long`/`Node` и массивы). |
| **[t5_redundant_checks.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t5_redundant_checks.py)** | **T5** | Избыточные проверки и блоки кода (невызываемый мёртвый код 0 сэмплов, дублируемая валидация по слоям). |
| **[t6_db_queries.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t6_db_queries.py)** | **T6** | Ошибки в запросах к базе данных (N+1 SQL-запросы, непакетированные записи, истощение HikariPool). |
| **[t7_memory_leak.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t7_memory_leak.py)** | **T7** | Утечка памяти (накопление объектов в Old Gen, растущие вызовы удержания коллекций/кэшей). |
| **[t8_memory_bloat.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t8_memory_bloat.py)** | **T8** | Перерасход памяти (In-Memory фильтрация и пагинация через Java Streams вместо SQL). |
| **[t9_cpu_hotspots.py](file:///Users/stanislavkhoshov/Documents/burn-job/scripts/analyzers/t9_cpu_hotspots.py)** | **T9** | Избыточная нагрузка на CPU (горячие методы приложения, блокировки и конкуренция потоков). |

---

## 🚀 Инструкция по использованию

### 1. Импорт профиля в графовую БД (`jfr_to_graph.py`)
```bash
python3 scripts/jfr_to_graph.py \
  --input app_profiling_full.collapsed \
  --db-path ./profiler_graph.db \
  --run-id commit_abc123
```

---

### 2. Запуск отдельного анализатора таксономии
Каждый анализатор из `scripts/analyzers/` можно запустить автономно:
```bash
# Проверить только неэффективные алгоритмы (T2)
python3 scripts/analyzers/t2_inefficient_algos.py --db-path ./profiler_graph.db

# Проверить только ошибки БД (T6)
python3 scripts/analyzers/t6_db_queries.py --db-path ./profiler_graph.db
```

---

### 3. Комплексный запуск через оркестратор (`analyze_anomalies.py`)

#### Запуск всех проверок T1–T9:
```bash
python3 scripts/analyze_anomalies.py --db-path ./profiler_graph.db
```

#### Запуск выборочных категорий (например, T1, T2 и T6):
```bash
python3 scripts/analyze_anomalies.py --db-path ./profiler_graph.db --category T1,T2,T6
```

#### Вывод результатов в формате JSON:
```bash
python3 scripts/analyze_anomalies.py --db-path ./profiler_graph.db --json
```

---

### 4. Сравнение двух прогонов профилирования (`compare_runs.py`)
```bash
python3 scripts/compare_runs.py \
  --db-path ./profiler_graph.db \
  --base-run run_v1 \
  --target-run run_v2
```

---

## 🛡️ 7. Чего мы НЕ считаем дефектом (Non-Defect Rules)

Автоматическая система анализа и классификации (`non_defects.py`) исключает или помечает как `NON_DEFECT` следующие 6 категорий паттернов:

1. **Порядок объявления полей в классе (`NON_DEFECT_FIELD_ORDERING`):**
   HotSpot раскладывает поля сам, порядок в исходнике на размер объекта не влияет (JOL на Java 21: 40 байт vs 40 байт).
2. **Квадратичная сложность при ограниченном входе (`NON_DEFECT_BOUNDED_QUADRATIC`):**
   Если API гарантирует $N \le 8$ элементов, вложенный цикл за наносекунды не является дефектом производительности.
3. **Кеш с заданной границей и политикой вытеснения (`NON_DEFECT_BOUNDED_CACHE`):**
   Рост размера кеша до границы — ожидаемое проектное поведение, а не утечка памяти.
4. **Хранение промежуточной коллекции, ограниченной параметром запроса (`NON_DEFECT_BOUNDED_REQUEST_COLLECTION`):**
   Размер коллекции ограничен проверенным максимумом пагинации (`pageSize`).
5. **Стоимость, измеримая только в микробенчмарке без нагрузки (`NON_DEFECT_MICROBENCHMARK_NOISE`):**
   Микрооптимизации, дающие эффект только в синтетике и теряющиеся в шуме I/O / обращения к БД.
6. **Стиль кода, не влияющий на поведение (`NON_DEFECT_CODE_STYLE`):**
   Форматирование, фигурные скобки, длина строк, порядок методов в файле.
