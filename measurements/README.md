# measurements — статус

Сюда сохраняются сырые артефакты замеров «до»/«после», снятые по каналам из `PROFILING.md`:

- снимки метрик (`./scripts/metrics-snapshot.sh before|after target/*.json` → `jvm.memory.used`,
  `jvm.memory.usage.after.gc`, `hibernate.statements`, `http.server.requests`);
- вывод `ab` (Apache Bench) и/или циклов `curl` для latency/RPS;
- записи JFR (`./scripts/jfr-dump.sh`, `jfr summary`, `./scripts/hot-frames.sh`);
- снимки `jcmd GC.heap_info`, `GC.class_histogram` при разборе утечек памяти.

Наполнение этой директории не автоматизировано кодом `burn_job` — это ручной шаг воспроизведения
замеров по процедуре `PROFILING.md` (раздел 5, «Порядок одного замера»), результаты которого затем
используются как `evidence.before`/`evidence.after` в `reports/sandbox/findings.json`.

## Текущий статус

Пусто — замеры в этом окружении ещё не сняты (пайплайн не запускался, см. `MANIFEST.md`, раздел 6).
