# runlog — статус

Здесь будет лежать `agent_run.log` — лог работы артефакта (что читал, что предлагал, что менял),
согласно требованию `SUBMISSION.md`.

Пишется функцией `_log()` (`src/burn_job/report/builder.py:92-98`) в путь `RUN_LOG_PATH`
(`src/burn_job/core/config.py:37`, по умолчанию `./runlog/agent_run.log`, переопределяется
`BURN_JOB_LOG_PATH` в `.env`).

## Текущий статус

Не сгенерирован — реальный прогон в этом окружении ещё не выполнялся, см. `MANIFEST.md`, раздел 6.
