# 003 — Метод → файл/строка (source mapping)

## Problem

Ни один компонент пайплайна сейчас не умеет превратить `Method.id` (вида
`com/example/badhibernate/service/NPlusOneService.getDepartmentsSubOptimal`) в
`file`/`line_from`/`line_to`. Это единственное, чего не хватает, чтобы `findings.json`
(схема из `TASK/SUBMISSION.md`) формировался автоматически, а не писался руками, как сейчас
в `skill/scripts/export_report.py:19-105`.

Дополнительная сложность, с которой мы столкнулись на практике в этой сессии: лямбды и
synthetic-методы в стеке (`BaseApp$$Lambda$1.0x00007af37c000a08.accept`) не резолвятся напрямую —
у них нет собственного `LineNumberTable`, нужно уметь схлопывать их к охватывающему методу.

## Goal

Дать функцию/CLI `resolve_source_location(method_fqn: str) -> Optional[(file, line_from, line_to)]`,
которая по полному имени метода находит файл и диапазон строк в `src/main/java/**`.

## Non-goals

- Не строить полноценный AST-анализатор — это часть более поздних спек ([008](008-static-callgraph-reachability-t5.md),
  [009](009-static-pattern-detection-t1-t2-t3-t6.md)), которые могут переиспользовать этот резолвер,
  но сами в эту спеку не входят.
- Не пытаться резолвить фреймы JDK/фреймворков (`java.*`, `org.hibernate.*`) — только код проекта
  (`className` по префиксу пакетов, найденным в `src/main/java`).

## Approach

1. На старте пайплайна один раз построить индекс `FQN класса → путь файла`, сканируя
   `src/main/java/**/*.java` (простое соответствие пакет+имя класса → путь, без парсинга тела).
2. Для точного диапазона строк метода — два источника, в порядке предпочтения:
   - **Bytecode debug info**: скомпилированные `.class` из `target/classes` (если Maven-проект
     уже собран) читаются через `javap -l -p <class>`, откуда парсится `LineNumberTable` для
     нужного метода — даёт точные `line_from`/`line_to`.
   - **Фолбэк на AST**: если `.class`-файлов нет (Maven не собирался), лёгкий построчный поиск
     сигнатуры метода в исходнике по имени класса+метода (regex по объявлению метода) — даёт
     приблизительный `line_from`, `line_to` эвристически как следующее объявление метода/закрывающую
     скобку того же уровня отступа.
3. Резолюция synthetic/lambda-фреймов: если `methodName` содержит `$$Lambda` или `lambda$`,
   отрезать суффикс и резолвить охватывающий метод (по конвенции javac `lambda$outerMethod$N`).
4. Результат кэшируется в памяти на время одного запуска (метод → локация не меняется в рамках
   одного анализа).

## Files touched

- `skill/scripts/source_mapping.py` (новый файл: `resolve_source_location`, индекс классов,
  парсинг `javap -l`, фолбэк на regex-поиск, резолюция lambda)

## Acceptance criteria

- [ ] Для метода из существующего demo-кода (например
      `com.example.badhibernate.service.NPlusOneService.getDepartmentsSubOptimal`) резолвер
      возвращает путь `src/main/java/com/example/badhibernate/service/NPlusOneService.java` и
      диапазон строк, пересекающийся с уже известным вручную диапазоном (27-38 в текущем
      `reports/sandbox/findings.json`).
- [ ] На lambda-фрейме (`Foo$$Lambda$N.accept`) возвращается локация охватывающего метода `Foo`,
      а не `None` и не ошибка.
- [ ] На фрейме из JDK/фреймворка (`java.util.HashMap.put`) возвращается `None` без исключения.
- [ ] Работает как при наличии собранных `.class`-файлов, так и без них (через regex-фолбэк) —
      проверяется явным тестом на обоих путях.

## Dependencies

Нет (независимая спека, использует только исходники и, опционально, `target/classes`).
[004](004-findings-json-generator.md) зависит от неё.
