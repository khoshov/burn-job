# PROFILING.md — Инструкция по профилированию sensorhub

## Профили запуска

1. `dev` — H2 in-memory БД, лёгкий сид (200 станций).
2. `load` — PostgreSQL 17.10, полный сид (2000 станций, 300к отсчётов).
3. `leak` — Наблюдение за утечками памяти при ограниченном heap.

## Метрики Actuator
- `/actuator/prometheus`
- `/actuator/metrics`
- `/actuator/heapdump`
- `/actuator/threaddump`
