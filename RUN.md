# RUN — Инструкция по запуску с нуля

Документ описывает процедуру развертывания и запуска артефакта **Burn Job** для анализа и автоматического рефакторинга целевого Java-сервиса.

---

## 1. Системные требования

- **Python**: 3.10 или выше
- **Java JDK**: 17 или 21 (`JAVA_HOME` настроен)
- **Apache Maven**: 3.8+

---

## 2. Быстрый запуск из корня проекта (Zero-Config)

```bash
# 1. Настройка переменных окружения (скопируйте шаблон)
cp .env.example .env

# 2. Запуск полного автономного 8-этапного цикла (анализ + детекторы + рефакторинг):
./run.sh
```

---

## 3. Запуск отдельных шагов пайплайна

```bash
# Сканирование REST Controller эндпоинтов:
./run.sh scan --src ./java/src/main/java

# Инжест трейсов async-profiler / JFR в KùzuDB:
./run.sh ingest --profile ./app_profiling_full.collapsed --db ./profiler_graph.db

# Запуск с локальной моделью Qwen3 через llama.cpp:
./run.sh run-cycle --backend llama.cpp --model-path Qwen3-4B/qwen3-4b-instruct.gguf

# Запуск с локальным/внешним vLLM сервером:
./run.sh run-cycle --backend vllm --model-path Qwen3-4B
```

---

## 4. Запуск через Docker

```bash
# Сборка и запуск контейнера:
docker compose up
```

---

## 5. Запуск тестов верификации

```bash
# Запуск единого пакета unit, integration и contract тестов:
.venv/bin/pytest
# или через make:
make test
```
