# RUN — Инструкция по запуску с нуля

Документ описывает процедуру развёртывания и запуска артефакта **Burn Job**
для анализа и автоматического рефакторинга целевого Java-сервиса
(`test_project` / sensorhub).

---

## 1. Системные требования

- **Python**: 3.10 или выше
- **Java JDK**: **21** (`JAVA_HOME` настроен на JDK 21 — обязательно, `pom.xml`
  проекта использует `java.version=21` и синтаксис records/pattern matching)
- **Apache Maven**: 3.8+
- **PostgreSQL**: локальный инстанс для `load`-профиля `test_project`

---

## 2. Установка Burn Job

```bash
git clone https://github.com/khoshov/burn-job.git
cd burn-job

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

---

## 3. Конфигурация `.env`

```bash
cp .env.example .env
```

Заполните в `.env`:

```env
BURN_JOB_SRC_DIR=./test_project/src/main/java
DEEPSEEK_API_KEY=sk-ваш_ключ_здесь
DEEPSEEK_MODEL=deepseek-v4-flash
BURN_JOB_BACKEND=openai
```

---

## 4. Поднять PostgreSQL для `test_project` (профиль `load`)

`test_project/src/main/resources/application-load.yaml` ожидает Postgres на
`localhost:55432`, пользователь/пароль `postgres`/`postgres`:

```bash
sudo systemctl start postgresql
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
# Слушать порт 55432 в дополнение к штатному 5432 (или перенастроить порт в postgresql.conf)
```

Для разработки без Postgres можно использовать dev-профиль на встроенной H2:

```bash
cd test_project && ./scripts/run-dev.sh
```

---

## 5. Сборка целевого проекта

```bash
cd test_project
mvn clean verify -q
cd ..
```

---

## 6. Запуск целевого сервиса

```bash
cd test_project
./scripts/run-load.sh   # профиль load, PostgreSQL, реалистичный объём сида
# или
./scripts/run-dev.sh    # профиль dev, встроенная H2, для быстрой проверки
cd ..
```

---

## 7. Запуск полного цикла Burn Job

```bash
source .venv/bin/activate

# Полный 8-этапный цикл: детекция + LLM-варианты фиксов + бенчмарк + применение
burn-job run-cycle --src test_project/src/main/java --variant-llm deepseek --apply

# Только rule-based детекция без LLM/бенчмарка (быстрая проверка)
burn-job detect --src test_project/src/main/java --db ./profiler_graph.db
```

Результаты:
- `reports/sandbox/findings.json` — машиночитаемые находки (схема `SUBMISSION.md`)
- `reports/sandbox/report.md` — человекочитаемый отчёт
- `loadtest/api_loadtest_suite.py` — сгенерированный нагрузочный тест
- `runlog/agent_run.log` — лог работы артефакта
- Правки, применённые к `test_project/src/main/java` (если `--apply`) — патч/ссылку на PR
  с этими правками сохраните в `pr/`
- `measurements/` — сюда вручную сохраняются сырые артефакты замеров «до»/«после» по
  каналам из `PROFILING.md` (снимки `metrics-snapshot.sh`, вывод `ab`, записи JFR); см. шаг 9.5 ниже

---

## 8. Запуск отдельных шагов пайплайна

```bash
burn-job scan --src test_project/src/main/java
burn-job ingest --profile ./app_profiling_full.collapsed --db ./profiler_graph.db
burn-job jfr2collapsed ./app_profiling.jfr
burn-job profile --pid <PID> --duration 30 --output ./app_profiling.jfr
```

---

## 9. Запуск тестов верификации

```bash
# Тесты burn-job (unit/integration/contract)
.venv/bin/pytest tests/ -v
# или: make test

# Проверка, что test_project остаётся зелёным после применённых правок
cd test_project && mvn test-compile && mvn test
```

---

## 9.5. Сохранение доказательств замера и патча

После прогона сохраните сырые артефакты, на которые ссылается `evidence` в `findings.json`
(процедура и каналы — `PROFILING.md`, раздел 5):

```bash
# снимки метрик "до"/"после"
./test_project/scripts/metrics-snapshot.sh before measurements/before.json
# ... нагрузка ...
./test_project/scripts/metrics-snapshot.sh after  measurements/after.json

# вывод ab / JFR-дампы — туда же, в measurements/
ab -n 200 -c 1 'http://localhost:8080/api/...' > measurements/ab_output.txt
```

Патч или ссылку на PR с правками, применёнными `--apply`, сохраните в `pr/` (например,
`git diff > pr/patch.diff` или файл со ссылкой на PR).

---

## 10. Запуск через Docker (альтернативный способ)

```bash
DEEPSEEK_API_KEY=sk-ваш_ключ docker compose up
```
