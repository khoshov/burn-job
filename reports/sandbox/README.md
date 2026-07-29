# reports/sandbox — статус

Согласно `SUBMISSION.md`, здесь должны лежать:

- `findings.json` — машиночитаемые находки (схема описана в `SUBMISSION.md`);
- `report.md` — человекочитаемый отчёт;
- `report.html` — дополнительный HTML-вариант отчёта (не требуется схемой, генерируется тем же шагом).

Все три файла пишет `AutonomousOrchestrator` на финальном этапе пайплайна
(`src/burn_job/pipeline/orchestrator.py:342-352`) при запуске:

```bash
burn-job run-cycle --src test_project/src/main/java --variant-llm deepseek --apply
```

## Текущий статус

Реальный прогон в этом окружении **ещё не выполнялся** — см. `MANIFEST.md`, раздел 6 («Статус»).
Этот файл — только каркас директории (git не отслеживает пустые папки); после прогона он может быть
удалён или оставлен рядом с `findings.json`/`report.md`.
