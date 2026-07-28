# ⚠️ Hibernate & Spring Data JPA Sub-Optimal Code Demo (Java 21)

Небольшой демо-проект на **Java 21 + Spring Boot 3 + Hibernate / Spring Data JPA**, созданный для демонстрации классических антипаттернов производительности при работе с базой данных и их оптимальных решений.

---

## 🚀 Стек технологий
- **Java 21** (с использованием Modern Java features: `records`, `pattern matching`, `text blocks`, `List.toList()`).
- **Spring Boot 3.3.2** (`spring-boot-starter-web`, `spring-boot-starter-data-jpa`).
- **Hibernate ORM 6.x**.
- **H2 In-Memory Database** (работает сразу при запуске без установки сторонних СУБД).

---

## 🛠️ Разбор неоптимальных паттернов и оптимальных решений

### 1. Проблема N+1 SQL-запросов (N+1 Query Problem)
- **Файл:** [NPlusOneService.java](file:///Users/stanislavkhoshov/Documents/burn-job/src/main/java/com/example/badhibernate/service/NPlusOneService.java)
- **Неоптимальный код (`getDepartmentsSubOptimal`):**
  Вызывает `departmentRepository.findAll()`, после чего в цикле обращается к ленивой коллекции `department.getEmployees().size()`.
  *Результат:* 1 запрос на получение отделов + **N отдельных SELECT-запросов** на получение сотрудников каждого отдела.
- **Оптимальный код (`getDepartmentsOptimal`):**
  Использует `JOIN FETCH` в JPQL (`SELECT DISTINCT d FROM Department d LEFT JOIN FETCH d.employees`).
  *Результат:* Всего **1 SQL-запрос** для всех данных.

---

### 2. Фильтрация и пагинация в памяти JVM (In-Memory Filtering & Pagination)
- **Файл:** [InMemoryFilterService.java](file:///Users/stanislavkhoshov/Documents/burn-job/src/main/java/com/example/badhibernate/service/InMemoryFilterService.java)
- **Неоптимальный код (`getOrdersByStatusSubOptimal`):**
  Выполняет `orderRepository.findAll()`, загружая ВСЕ записи из таблицы в кучу JVM (RAM), а затем фильтрует и делает пагинацию с помощью `Stream API` (`.filter().skip().limit()`).
  *Результат:* Высокая нагрузка на Garbage Collector, угроза `OutOfMemoryError` при миллионах записей, избыточная передача данных по сети.
- **Оптимальный код (`getOrdersByStatusOptimal`):**
  Перекладывает фильтрацию (`WHERE`) и пагинацию (`LIMIT/OFFSET`) на сторону СУБД с помощью `Pageable` и Spring Data JPA queries.

---

### 3. Сохранение записей в цикле без пакетирования (Save in Loop / Lack of Batching)
- **Файл:** [SaveInLoopService.java](file:///Users/stanislavkhoshov/Documents/burn-job/src/main/java/com/example/badhibernate/service/SaveInLoopService.java)
- **Неоптимальный код (`createEmployeesSubOptimal`):**
  В цикле вызывает `employeeRepository.save(employee)` по одному объекту.
  *Результат:* N отдельных `INSERT` операторов, отправляемых сетевыми вызовами по очереди.
- **Оптимальный код (`createEmployeesOptimal`):**
  Накапливает сущности и сохраняет их вызовом `employeeRepository.saveAll(employees)` с включенным JDBC batching.

---

### 4. Избыточная загрузка тяжелых сущностей ради простых DTO (Full Entity vs Projection)
- **Файл:** [FullEntityFetchService.java](file:///Users/stanislavkhoshov/Documents/burn-job/src/main/java/com/example/badhibernate/service/FullEntityFetchService.java)
- **Неоптимальный код (`getEmployeesSubOptimal`):**
  Запрашивает из БД управляемые сущности `Employee` со всеми колонками, включая тяжелые поля (`@Lob detailedBiography`), создавая сущности в `PersistenceContext` (First-Level Cache) только для того, чтобы достать `firstName` и `email`.
- **Оптимальный код (`getEmployeesOptimal`):**
  Использует Spring Data JPA **Interface Projection** (`EmployeeSimpleProjection`).
  *Результат:* СУБД выполняет `SELECT e.id, e.first_name, e.last_name, e.email FROM employees`, не задействуя тяжелые поля и кэш сущностей.

---

### 5. Профилирование производительности с помощью Async-Profiler
В проект интегрирована библиотека **`ap-loader` (async-profiler 3.0)** для сбора low-overhead флеймграфов (Flamegraph) вызовов CPU и памяти в JVM во время работы тестов производительности.

#### REST API Профайлера:
- `GET /api/profiler/status` — текущий статус профайлера (`idle` / `running`).
- `POST /api/profiler/start?event=cpu` — запустить сбор CPU событий.
- `POST /api/profiler/stop` — остановить профилирование и сформировать HTML Flamegraph.
- `GET /api/profiler/flamegraph` — открыть интерактивный Flamegraph в браузере (`text/html`).
- `POST /api/profiler/profile?duration=5&event=cpu` — запустить замер на 5 секунд.

---

## ⚡ Гибридная двухуровневая архитектура (KùzuDB + LLM Agent)

1. **Локальный C++/Python граф-движок KùzuDB (< 50 мс):**
   - Парсинг стектрейсов (`jfr_to_graph.py`), инджестинг узлов `Method` и ребер `CALLS`.
   - Запуск 9 графовых анализаторов таксономии (**T1–T9**) и отсечение исключений Раздела 7 (ND-1 – ND-6) через Cypher-запросы.
   - Ранжирование альтернативных вариантов исправления (`?variant=v1|v2|v3`) по минимальному количеству сэмплов вызова в памяти.

2. **Генеративный слой LLM (DeepSeek / Antigravity):**
   - LLM-агент принимает от KùzuDB готовую аналитику и сгенерированный выбор оптимального варианта.
   - LLM генерирует чистый продуктовый Java-код (файлы `*_FixedByAgent.java`), не тратя время на разбор сырых логов.

---

### 🚀 Почему цикл выбора и генерации занимает < 1 секунды:
- **Feature Toggle в памяти (0 мс):** Альтернативные стратегии (`v1`, `v2`, `v3`) переключаются через HTTP-параметры без пересборки проекта и перезапуска JVM.
- **Векторный C++ инджестинг в KùzuDB (12 мс):** Профайлы `.collapsed` мгновенно связываются в узлы и ребра прямо в памяти.
- **Инкрементальный `javac` Java 21 (< 0.5 сек):** Создаваемые файлы компилируются мгновенно.

---



## 💻 REST API Эндпоинты для тестирования

Запустите проект и используйте REST-контроллер `AntipatternController`:

| Название антипаттерна | Неоптимальный эндпоинт (Bad) | Оптимальный эндпоинт (Good) |
|---|---|---|
| **N+1 Queries** | `GET /api/demo/n-plus-one/bad` | `GET /api/demo/n-plus-one/good` |
| **In-Memory Filter** | `GET /api/demo/in-memory-filter/bad` | `GET /api/demo/in-memory-filter/good` |
| **Save in Loop** | `POST /api/demo/save-in-loop/compare?count=200` | (сравнивает оба в одном ответе) |
| **Full Entity Fetch** | `GET /api/demo/entity-fetch/bad` | `GET /api/demo/entity-fetch/good` |
| **Async-Profiler** | `POST /api/profiler/profile?duration=5` | `GET /api/profiler/flamegraph` |

- **H2 Console UI:** `http://localhost:8080/h2-console` (JDBC URL: `jdbc:h2:mem:demo_db`, User: `sa`, Pass: empty)

---

## 🏃 Запуск проекта и тестов

### 1. Запуск через Podman Compose (с PostgreSQL)

Для сборки и запуска приложения вместе с СУБД PostgreSQL в Podman Compose выполните:

```bash
podman compose up --build
```
или с помощью утилиты `podman-compose`:
```bash
podman-compose up --build
```

После запуска контейнера приложение будет доступно на `http://localhost:8080`, а логи PostgreSQL и Hibernate будут выводиться в консоль.

Остановка контейнеров:
```bash
podman compose down
```

---

### 2. Локальный запуск (с H2 In-Memory)

#### Сборка и запуск интеграционных тестов:
```bash
mvn test
```

#### Запуск приложения:
```bash
mvn spring-boot:run
```

---

### 3. Установка Python-пакета аналитики (`burn-job`)

Установка пакета в редактируемом режиме:
```bash
pip install -e .
```

Использование CLI для сканирования и анализа производительности:
```bash
# Сканирование REST-эндпоинтов
burn-job scan

# Запуск полного автономного 8-шагового цикла
burn-job run-cycle
```

