# loadtest — статус

Требование `SUBMISSION.md`: для уровня `hard` обязателен собственный нагрузочный тест.

Здесь будет лежать `api_loadtest_suite.py` — Python-скрипт, автоматически сгенерированный
`LoadtestGenerator.generate_script()` на этапе 2 пайплайна (пути — `src/burn_job/pipeline/loadtest.py:16-58`,
вызов из `src/burn_job/pipeline/orchestrator.py:306-307`) на основе эндпоинтов, найденных на этапе 1
(сканирование `@RestController`).

## Текущий статус

Не сгенерирован — реальный прогон (`burn-job run-cycle`) в этом окружении ещё не выполнялся,
см. `MANIFEST.md`, раздел 6.
