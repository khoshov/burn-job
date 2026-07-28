# PROFILING.md — как мерить sensorhub

Документ описывает **каналы измерения** и **порядок прогона**. Готового нагрузочного плана здесь нет
намеренно: нагрузочный сценарий вы пишете сами.

---

## 1. Профили запуска

| Профиль | Команда | БД | Сид | Флаги JVM |
|---|---|---|---|---|
| `dev` | `./scripts/run-dev.sh` | H2 in-memory | малый (200 станций / 1 000 измерений / 20 000 отсчётов) | по умолчанию |
| `load` | `./scripts/run-load.sh` | встроенный PostgreSQL 17.10, порт 55432 | полный (2 000 / 10 000 / 300 000) | `-Xms512m -Xmx512m`, G1, JFR, NMT |
| `load,leak` | `./scripts/run-leak.sh` | встроенный PostgreSQL 17.10, порт 55432 | урезанный (плоская таблица 20 000) | `-Xms384m -Xmx384m`, `ExitOnOutOfMemoryError`, `MaxDirectMemorySize=64m` |

**Замеры снимаются только на `load` (и `load,leak` для памяти).**

### Почему не на H2

Измерено на одном и том же коде, одинаковых данных:

| Стенд | Правка «убрать лишние обращения в БД» | Правка «не тащить таблицу в heap» |
|---|---|---|
| H2 in-memory | 66.5 → 54.5 мс — **1.2x** | измерить нельзя: данные уже лежат в том же heap |
| Встроенный PostgreSQL 17.10 | 465.8 → 17.0 мс — **27.4x** | 158.9 → 15.9 мс — **10.0x** |

H2 in-memory живёт в heap приложения, поэтому round-trip к базе почти бесплатен, а baseline памяти
испорчен самими данными. Правильная правка на H2 даёт неубедительные цифры. Для замеров H2 не годится.

---

## 2. Подъём стенда

```bash
./scripts/db-reset.sh            # перед каждой серией замеров: чистое состояние БД
./mvnw -B clean package
./scripts/run-load.sh
```

Первый `db-up.sh` на машине — около **11.5 с** (распаковка бинарников PostgreSQL в `/tmp/embedded-pg`),
все последующие — около **582 мс**. Это не зависание. `/tmp/embedded-pg` удалять не нужно: удаление
возвращает старт к 11.5 с.

Между прогонами журнальные таблицы чистятся:

```bash
curl -s -X POST localhost:8080/internal/reset -o /dev/null -w '%{http_code}\n'
```

---

## 3. Обязательный шаг: убить процесс перед прогоном

```bash
./scripts/kill-app.sh
```

Причина измерена: `OutOfMemoryError` прилетает в поток `http-nio-8080-exec-N`, **процесс при этом
остаётся жив**, продолжает слушать порт 8080 в деградированном состоянии и роняет следующий запуск
сообщением «Port 8080 was already in use». Скрипты `run-*.sh` вызывают `kill-app.sh` сами, но при
ручном запуске его надо выполнять явно.

Для замеров памяти рестарт процесса перед каждым измерением обязателен: без него сравниваются
не два состояния кода, а два состояния прогретого heap.

---

## 4. Каналы измерения

### 4.1. Обращения в базу

| Канал | Команда | Замечание |
|---|---|---|
| заголовок ответа `X-Sql-Count` | `curl -s -D - -o /dev/null 'localhost:8080/api/reports/daily?from=2026-04-01&to=2026-04-07'` | считает запросы **этого** HTTP-вызова, корректен при любой конкурентности |
| `hibernate.statements` | `curl -s localhost:8080/actuator/metrics/hibernate.statements` | счётчик глобальный на JVM: дельта валидна только при `-c 1` |
| гидрация сущностей | `curl -s localhost:8080/actuator/metrics/hibernate.entities.loads` | на выборке из 50 строк даёт ровно +50 |
| время запроса | заголовок `X-Elapsed-Ms` | |

Заголовки `X-Sql-Count` и `X-Elapsed-Ms` ставит измерительная обвязка на каждый ответ.

Лог SQL по умолчанию выключен. Включается на время разбора:

```bash
curl -s -X POST localhost:8080/actuator/loggers/org.hibernate.SQL \
  -H 'Content-Type: application/json' -d '{"configuredLevel":"DEBUG"}'
```

### 4.2. Время и пропускная способность

```bash
ab -n 200 -c 1 'http://localhost:8080/api/reports/daily?from=2026-04-01&to=2026-04-07'
curl -s localhost:8080/actuator/metrics/http.server.requests | python3 -m json.tool
```

`http.server.requests` даёт `COUNT`, `TOTAL_TIME` и `MAX`; p95 берётся из вывода `ab`.
Для URL с меняющимся параметром `ab` не годится — нужен цикл `curl`.

Первый прогон всегда завышен в разы: **прогрев обязателен**, замер берётся после него,
как лучшее (или медиана) из нескольких повторов.

### 4.3. Память

```bash
curl -s 'localhost:8080/actuator/metrics/jvm.memory.used?tag=area:heap'
curl -s  localhost:8080/actuator/metrics/jvm.memory.usage.after.gc
```

**Фильтр `?tag=area:heap` обязателен.** Без него метрика суммирует heap и non-heap: на свежем
приложении это **163 МБ против 65 МБ** heap-only — разница в 2.5 раза, целиком за счёт metaspace,
code cache и compressed class space.

Для тренда памяти (растёт ли удержание) — снимок в 3–4 точках прогона:

```bash
PID=$(pgrep -f sensorhub-1.0.0.jar | head -1)
jcmd "$PID" GC.run && jcmd "$PID" GC.run && jcmd "$PID" GC.heap_info
```

Два `GC.run` подряд — не суеверие: одна сборка не гарантирует, что мусор молодого поколения ушёл.
Доказательством роста удержания является **тренд после полной сборки**, а не единичный факт OOM.

Готовый снимок всех метрик разом:

```bash
./scripts/metrics-snapshot.sh before target/before.json
# ... нагрузка ...
./scripts/metrics-snapshot.sh after  target/after.json
```

Дополнительно:

```bash
jcmd "$PID" GC.class_histogram | head -30      # что именно копится
jcmd "$PID" VM.native_memory summary           # off-heap, требует -XX:NativeMemoryTracking=summary
curl -s localhost:8080/actuator/metrics/jvm.gc.memory.allocated   # темп аллокаций
curl -s localhost:8080/actuator/metrics/jvm.gc.pause              # SUM и MAX пауз
```

### 4.4. CPU и горячие кадры

```bash
curl -s localhost:8080/actuator/metrics/process.cpu.time     # дельту берём между двумя снимками
./scripts/jfr-dump.sh                                        # сброс записи + jfr summary
./scripts/hot-frames.sh target/run.jfr                       # топ-20 кадров
```

Прогоны `run-load.sh` и `run-leak.sh` включают JFR сами (`settings=profile`, дамп при выходе).
Начать отдельную запись вручную — `./scripts/jfr-start.sh`.

**Предупреждение:** на простаивающем приложении событий `jdk.ExecutionSample` почти нет — в проверочной
записи их было 6 штук. Профилировать надо **под нагрузкой и не менее 30 секунд**, иначе картина горячих
кадров пуста или случайна. Это одна из причин, по которой нагрузочный сценарий нужен собственный.

Полезные события JFR: `jdk.ExecutionSample` (CPU), `jdk.ObjectAllocationSample` (аллокации),
`jdk.JavaExceptionThrow` (исключения в горячем пути), `jdk.OldObjectSample` (что удерживается).

```bash
jfr summary target/load.jfr
jfr print --events jdk.JavaExceptionThrow target/load.jfr | head -60
```

### 4.5. Прочее

```bash
curl -s localhost:8080/actuator/prometheus | grep -E '^(hibernate|jvm_memory|http_server)'
curl -s localhost:8080/actuator/metrics/hikaricp.connections.pending
curl -s localhost:8080/actuator/threaddump -H 'Accept: application/json' > target/threads.json
curl -s localhost:8080/actuator/heapdump -o target/manual.hprof
```

---

## 5. Порядок одного замера

1. `./scripts/kill-app.sh`
2. `./scripts/db-reset.sh` (перед серией) или `POST /internal/reset` (между прогонами внутри серии)
3. `./mvnw -B clean package`
4. `./scripts/run-load.sh`, дождаться строки о старте и завершении сида
5. прогрев: несколько десятков вызовов измеряемого эндпоинта, результаты отбрасываются
6. `./scripts/metrics-snapshot.sh before …` → нагрузка → `./scripts/metrics-snapshot.sh after …`
7. точечные снимки: JFR, `GC.heap_info`, при необходимости гистограмма классов
8. `./scripts/kill-app.sh` перед следующим прогоном

«После» снимается **тем же способом на том же стенде**: другой профиль, другой объём данных
или другая машина сравнению не подлежат.

---

## 6. Обоснование флагов JVM

| Флаг | Зачем |
|---|---|
| `-Xms` = `-Xmx` | убирает шум расширения heap, делает `usage.after.gc` сопоставимым между прогонами |
| `-Xmx512m` (`load`) / `384m` (`leak`) | эффект виден, но процесс доживает до конца прогона |
| `-XX:+UseG1GC` | один и тот же сборщик во всех прогонах |
| `-XX:+ExitOnOutOfMemoryError` (`leak`) | детерминированное завершение: иначе процесс живёт и держит порт |
| `-XX:+HeapDumpOnOutOfMemoryError` | материал для разбора |
| `-XX:StartFlightRecording=…,settings=profile` | CPU-профиль без внешних профайлеров |
| `-XX:NativeMemoryTracking=summary` | доказать, что рост идёт в heap, а не вне его |
| `-XX:MaxDirectMemorySize=64m` (`leak`) | ни один прогон не может съесть всю память машины через direct-буферы |
| `-Duser.language=en -Duser.country=US` | машина может быть в `ru_RU`, тогда `%.3f` даёт запятую и CSV расходится |
| `-Duser.timezone=UTC` | детерминированные границы суток в отчётах |

---

## 7. Инструменты

`ab` и цикл `curl` — основные средства нагрузки. `jcmd`, `jfr` входят в Temurin 21
(`$JAVA_HOME/bin/`). k6 на стенде судейства нет. Внешние профайлеры не требуются: встроенного JFR
достаточно.
