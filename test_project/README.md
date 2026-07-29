# sensorhub — Сервис телеметрии сети метеостанций

## 1. Описание

Сервис `sensorhub` предназначен для приёма, хранения и анализа измерений датчиков сети метеостанций.
Проект используется для проведения нагрузочного тестирования и профилирования производительности.

## 2. Стек технологий

- **Java 21**
- **Spring Boot 3.4.2**
- **Spring Data JPA**
- **H2 / PostgreSQL**
- **Caffeine Cache**
- **Micrometer & Prometheus**

## 3. Запуск

### Разработка (Dev profile, H2 in-memory)
```bash
./scripts/run-dev.sh
```

### Нагрузка (Load profile, PostgreSQL)
```bash
./scripts/run-load.sh
```

### Сборка и тесты
```bash
mvn -B clean verify
```
