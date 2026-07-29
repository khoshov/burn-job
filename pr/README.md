# pr — статус

Сюда попадает патч или ссылка на PR с правками, применёнными к `test_project/src/main/java` после
запуска:

```bash
burn-job run-cycle --src test_project/src/main/java --variant-llm deepseek --apply
```

Правки применяются исключительно движком `burn_job` (детекторы → LLM-варианты → бенчмарк → выбор
победителя → `mvn test-compile`), без ручного редактирования — см. `MANIFEST.md`, раздел 3.

## Текущий статус

Пусто — `--apply`-прогон в этом окружении ещё не выполнялся, см. `MANIFEST.md`, раздел 6.
