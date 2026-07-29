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

## 4. Инвентарь производительных дефектов (T1–T9)

Проект содержит **249 методов с дефектами** в 19 файлах (пакет `service/defects/`) +
**112 корректных реализаций** в 9 файлах (пакет `service/defects/correct/`) для проверки отсутствия false positives.

### T1 — Redundant Operations (30 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T1RedundantOperationsSuite` | `redundantSubstringInLoop` | `s.substring(0, Math.min(...))` в `+=` loop |
| `T1RedundantOperationsSuite` | `redundantReplaceAllInLoop` | одинаковый `replaceAll` дважды на итерацию |
| `T1RedundantOperationsSuite` | `redundantToLowerCaseInLoop` | `.toLowerCase().toLowerCase().toLowerCase()` |
| `T1RedundantOperationsSuite` | `redundantTrimStrip` | `.trim().strip().trim()` chain |
| `T1RedundantOperationsSuite` | `redundantFormatInLoop` | вложенный `String.format` в цикле |
| `T1MiscPatternsV2` | `redundantIsBlank` | `trim().stripLeading().stripTrailing()` после `isBlank()` |
| `T1MiscPatternsV2` | `redundantToStringOnString` | `s.toString().toString().trim()` |
| `T1MiscPatternsV2` | `redundantStringValueOfOnString` | `String.valueOf(val)` на String |
| `T1RedundantOperationsSuite` | `redundantStringValueOf` | `String.valueOf(i)` дважды на итерацию |
| `T1RedundantOperationsSuite` | `redundantStringConcatInFormat` | `a+b+c + "("+a+b+c+")"` |
| `T1RedundantOperationsSuite` | `redundantCollectionCopy` | 3× `List.copyOf(source)` + O(n³) |
| `T1RedundantOperationsSuite` | `redundantArrayLengthCheck` | два одинаковых цикла подряд |
| `T1MiscPatternsV2` | `collectToArrayList` | `.collect(Collectors.toList())` |
| `T1RedundantOperationsSuite` | `redundantBooleanCompare` | `flag == Boolean.TRUE` |
| `T1RedundantOperationsSuite` | `redundantMathAbs` | `Math.abs(value)` дважды |
| `T1MiscPatternsV2` | `fileExistsRepeatedly` | `f.exists() && f.exists() && f.isFile() && f.isFile()` |
| `T1MiscPatternsV2` | `mapContainsKeyThenGet` | containsKey + get вместо `getOrDefault` |
| `T1MiscPatternsV2` | `mapContainsKeyThenGetLoop` | containsKey + get в цикле |
| `T1MiscPatternsV2` | `redundantPutIfAbsent` | обе ветки вызывают `map.put(key, val)` |
| `T1RedundantOperationsSuite` | `redundantUuidCreation` | два UUID из одного входа |
| `T1MiscPatternsV2` | `optionalIsPresentGet` | `isPresent()` + `get()` вместо `orElse` |
| `T1MiscPatternsV2` | `twoInstantNowCalls` | третий лишний `Instant.now()` |
| `T1MiscPatternsV2` | `cachedLengthInLoop` | `items.size()` во внутреннем цикле |
| `T1MiscPatternsV2` | `redundantCopyPasteCatch` | одинаковые catch блоки |
| `SyntheticDefectsService` | `t1_duplicate_op_1/2` | copy-paste метод |
| `SyntheticDefectsService` | `t1_duplicate_calc_1/2` | copy-paste вычислений |
| `SyntheticDefectsService` | `t1_redundant_query_loop_1/2` | двойной запрос в цикле |

### T2 — Inefficient Algorithms (31 метод)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T2DataStructureMisuseV2` | `linkedListRandomAccess` | `list.get(i)` на LinkedList |
| `T2DataStructureMisuseV2` | `linkedListInsertAtEnd` | `list.add(0, s)` на LinkedList |
| `T2DataStructureMisuseV2` | `copyOnWriteWriteHot` | `CopyOnWriteArrayList.add()` в write-hot loop |
| `T2DataStructureMisuseV2` | `concurrentHashMapReadHeavy` | `synchronized(map)` на CHM |
| `T2DataStructureMisuseV2` | `hashtableInsteadOfHashMap` | `Hashtable` |
| `T2DataStructureMisuseV2` | `treeMapWithoutComparator` | лишний `TreeMap` |
| `T2DataStructureMisuseV2` | `stringBufferInsteadOfBuilder` | `StringBuffer` |
| `T2DataStructureMisuseV2` | `streamDistinctOnLargeData` | `.collect(ArrayList::new, …)` |
| `T2DataStructureMisuseV2` | `priorityQueueWithComplexComparator` | дорогой comparator |
| `T2DataStructureMisuseV2` | `treeSetWithSlowComparator` | length-based comparator |
| `T2DataStructureMisuseV2` | `stringSplitInLoop` | regex split в цикле |
| `T2DataStructureMisuseV2` | `integerToStringInLoop` | `Integer.toString(v)` в цикле |
| `T2InefficientAlgorithmsSuite` | `bubbleSort` | O(n²) sort |
| `T2InefficientAlgorithmsSuite` | `fibonacciRecursive` | O(2ⁿ) рекурсия |
| `T2InefficientAlgorithmsSuite` | `linearSearchInAllCombinations` | contains в обе стороны |
| `T2InefficientAlgorithmsSuite` | `countViaLinearLookup` | O(n²) word count |
| `T2InefficientAlgorithmsSuite` | `tripleNestedJoin` | O(n³) тройной цикл |
| `T2InefficientAlgorithmsSuite` | `listContainsInLoop` | O(n²) через contains |
| `T2InefficientAlgorithmsSuite` | `dedupViaList` | O(n²) dedup |
| `T2InefficientAlgorithmsSuite` | `sortInLoop` | полная сортировка N раз |
| `T2InefficientAlgorithmsSuite` | `matrixMultiplicationQuadratic` | дублированные O(n²) блоки |
| `T2InefficientAlgorithmsSuite` | `repeatedArrayToStream` | stream 100 раз |
| `T2InefficientAlgorithmsSuite` | `stringConcatInLoop` | `+=` во внутреннем цикле |
| `SyntheticDefectsService` | `t2_nested_loop_1/2` | вложенные циклы |
| `SyntheticDefectsService` | `t2_linear_search_contains_1` | `contains` в цикле |
| `SyntheticDefectsService` | `t2_linear_search_indexOf_2` | `indexOf` в цикле |
| `SyntheticDefectsService` | `t2_repeated_stream_sorting` | сортировка 10 раз |
| `DuplicateDetector` | `process` | `contains` на ArrayList |
| `StationStatsService` | `getStats` | вложенный цикл MetricType × RawSample |
| `FilterCombiner` | `combineFilters` | лишняя сортировка |

### T3 — Heavy Materialization (25 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T3ProjectionAndEagerV2` | `getStationTitlesFullEntity` | `findAll()` затем filter |
| `T3ProjectionAndEagerV2` | `getDistinctMetricsFullEntity` | `findAll()` для distinct |
| `T3ProjectionAndEagerV2` | `countActiveStationsFullEntity` | `findAll()` для count |
| `T3ProjectionAndEagerV2` | `getFirstStationTitleFullEntity` | `findAll()` для findFirst |
| `T3ProjectionAndEagerV2` | `findAllMaterialsCount` | 3× `findAll()` для count |
| `T3ProjectionAndEagerV2` | `sumAllMeasuredFullEntity` | `findAll()` для sum |
| `T3ProjectionAndEagerV2` | `anyMeasurementByMetricFullEntity` | `findAll()` для anyMatch |
| `T3ProjectionAndEagerV2` | `getStationIdsFromFullEntity` | `findAll()` для map(ID) |
| `T3HeavyMaterializationSuite` | `countStationsViaFindAll` | `findAll().size()` |
| `T3HeavyMaterializationSuite` | `getStationTitleFindAll` | `findAll()` затем search |
| `T3HeavyMaterializationSuite` | `getAllStationCodes` | `findAll()` для projection |
| `T3HeavyMaterializationSuite` | `hasMeasurementsFindAll` | `findAll()` для anyMatch |
| `T3HeavyMaterializationSuite` | `getMaxMeasuredFindAll` | `findAll()` для max |
| `T3HeavyMaterializationSuite` | `getAllMetricCodes` | `findAll()` на MetricType |
| `T3HeavyMaterializationSuite` | `countMetricTypes` | `findAll().size()` |
| `T3HeavyMaterializationSuite` | `getMeasurementsByMetricFindAll` | `findAll()` + filter |
| `T3HeavyMaterializationSuite` | `sumMeasuredFindAll` | `findAll()` вручную sum |
| `T3HeavyMaterializationSuite` | `existsByCodeFindAll` | `findAll()` + scan |
| `T3HeavyMaterializationSuite` | `distinctRegions` | `findAll()` + distinct |
| `T3HeavyMaterializationSuite` | `countRawSamplesViaFindAll` | `rawSampleRepository.findAll().size()` |
| `T3ProjectionAndEagerV2` | `entityGraphFullFetch` | EntityGraph с избыточной загрузкой |
| `T3ProjectionAndEagerV2` | `lazyOneToOneTrigger` | N+1 через entity graph |
| `SyntheticDefectsService` | `t3_existence_full_fetch_1/2/3` | full fetch для existence |

### T4 — Data Layout (27 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T4ObjectOverheadV2` | `bigDecimalInLoop` | `BigDecimal` создание в цикле |
| `T4ObjectOverheadV2` | `stringFormatOverhead` | `String.format` в цикле |
| `T4ObjectOverheadV2` | `stringConcatDefaultCapacity` | `StringBuilder()` без capacity |
| `T4ObjectOverheadV2` | `newStringCopy` | `new String(original)` |
| `T4ObjectOverheadV2` | `stringInternInLoop` | `t.intern()` в цикле |
| `T4ObjectOverheadV2` | `manySmallObjectsList` | `new String(…)` на итерацию |
| `T4ObjectOverheadV2` | `objectArrayVsPrimitive` | `Double[]` → `double[]` |
| `T4ObjectOverheadV2` | `largeObjectArrayOverhead` | `Object[]` с boxing |
| `T4ObjectOverheadV2` | `bigNumberToString` | `Integer.valueOf(value).toString()` |
| `T4ObjectOverheadV2` | `hashMapResizeOverhead` | HashMap без initial capacity |
| `T4ObjectOverheadV2` | `enumMapVsHashMap` | `HashMap` для enum keys |
| `T4ObjectOverheadV2` | `dateVsInstant` | `new Date()` вместо `Instant` |
| `T4ObjectOverheadV2` | `arrayListTrimToSize` | лишний `trimToSize()` |
| `T4DataLayoutSuite` | `sumDoublesBoxed` | `Double total = 0.0` с `+=` |
| `T4DataLayoutSuite` | `sumLongsBoxed` | `Long total = 0L` с `+=` |
| `T4DataLayoutSuite` | `sumIntegersBoxed` | `Integer total = 0` с `+=` |
| `T4DataLayoutSuite` | `sumFloatsBoxed` | `Float total = 0.0f` с `+=` |
| `T4DataLayoutSuite` | `boxedMapOverhead` | `Long.valueOf(i)` в цикле |
| `T4DataLayoutSuite` | `arrayListOfBoxedDoubles` | `ArrayList<Double>` с autoboxing |
| `T4DataLayoutSuite` | `boxedArrayAllocation` | `Double[]` с boxing |
| `T4DataLayoutSuite` | `integerObjectHashInHotPath` | `Objects.hashCode(v)` на Integer |
| `T4DataLayoutSuite` | `integerKeyBoxing` | `Map<Integer, String>` |
| `T4DataLayoutSuite` | `stringBuilderToStringInLoop` | `new StringBuilder(result).append(p)` |
| `T4DataLayoutSuite` | `toggleFlagBoxed` | `Boolean flag = current; flag = !flag` |
| `SyntheticDefectsService` | `t4_boxed_overhead_1/2` | boxed Double/Long |

### T5 — Dead Code & Redundant Checks (30 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T5OptionalAndControlFlowV2` | `optionalIsPresentThenGet` | `isPresent()` + `get()` |
| `T5OptionalAndControlFlowV2` | `emptyCatchBlock` | пустой catch |
| `T5OptionalAndControlFlowV2` | `catchRethrowSame` | catch + rethrow |
| `T5OptionalAndControlFlowV2` | `emptyFinallyBlock` | пустой finally |
| `T5OptionalAndControlFlowV2` | `identicalCatchBlocks` | одинаковые catch |
| `AuditWriter` | `logAccess` | пустой `catch (Exception ignored)` |
| `T5OptionalAndControlFlowV2` | `redundantElseAfterReturn` | else после return |
| `T5OptionalAndControlFlowV2` | `booleanMethodIfElse` | `if (x>0) true else false` |
| `T5OptionalAndControlFlowV2` | `assignmentInIfCondition` | присваивание в if |
| `T5OptionalAndControlFlowV2` | `redundantStreamConversion` | `.stream().forEach()` |
| `T5OptionalAndControlFlowV2` | `redundantToStringOnMethodResult` | `obj.toString()` |
| `T5OptionalAndControlFlowV2` | `redundantCollectionCheck` | лишний null+isEmpty guard |
| `T5OptionalAndControlFlowV2` | `uselessContinueInLoop` | continue в конце цикла |
| `T5OptionalAndControlFlowV2` | `redundantSuperCall` | пустое тело метода |
| `T5OptionalAndControlFlowV2` | `unusedPrivateField` | неиспользуемое поле |
| `T5RedundantChecksSuite` | `duplicateNullCheck` | `input == null` дважды |
| `T5RedundantChecksSuite` | `redundantStringCheck` | `val != null && val != null` |
| `T5RedundantChecksSuite` | `redundantToNullCheck` | null + isEmpty check |
| `T5RedundantChecksSuite` | `deadIfFalse` | `if (false)` |
| `T5RedundantChecksSuite` | `unreachableElseBranch` | недостижимая ветка else |
| `T5RedundantChecksSuite` | `emptyMethodBody` | пустое тело метода |
| `T5RedundantChecksSuite` | `unusedParameter` | неиспользуемый param |
| `T5RedundantChecksSuite` | `unusedAssignment` | вычисление перезаписано |
| `T5RedundantChecksSuite` | `alwaysTrueComparison` | `value >= 0 \|\| value < 0` |
| `T5RedundantChecksSuite` | `duplicateCondition` | `x > 0 && x > 0` |
| `T5RedundantChecksSuite` | `selfComparison` | `x > x` |
| `T5RedundantChecksSuite` | `redundantLocalVariable` | лишняя tmp переменная |
| `T5RedundantChecksSuite` | `redundantTernary` | `flag ? Boolean.TRUE : FALSE` |
| `T5RedundantChecksSuite` | `redundantInstanceOf` | лишний instanceof |
| `SyntheticDefectsService` | `t5_redundant_null_checks` | двойной null check |

### T6 — Database Bottlenecks (29 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T6DatabaseBottlenecksSuite` | `nPlusOneViaLazyCollection` | `s.getMeasurements().size()` в цикле |
| `T6DatabaseBottlenecksSuite` | `lazyAccessInLoop` | вложенный N+1 |
| `T6DatabaseBottlenecksSuite` | `repeatedCountQuery` | findByCode + lazy size |
| `T6JoinFetchPaginationV2` | `findAndAccessLazy` | lazy access в stream |
| `T6JoinFetchPaginationV2` | `nPlusOneViaManyToMany` | lazy после JPQL |
| `SyntheticDefectsService` | `t6_n_plus_one_lazy_load` | lazy N+1 |
| `T6DatabaseBottlenecksSuite` | `findByIdInLoop` | `findById` в цикле |
| `T6DatabaseBottlenecksSuite` | `nPlusOneFindByCode` | `findByCodeIgnoreCase` в цикле |
| `T6JoinFetchPaginationV2` | `countThenQueryInLoop` | двойной запрос на итерацию |
| `CsvExportService` | `exportSamples` | `findById` inside computeIfAbsent |
| `DailyReportService` | `getDailyReport` | `findById` per group |
| `TopReportService` | `getTop` | `findById` в stream.map |
| `MeasurementSearchService` | `search` | `findById` в page.map |
| `T6DatabaseBottlenecksSuite` | `nPlusOneEveryMetricType` | findAll + filter per type |
| `T6DatabaseBottlenecksSuite` | `saveInLoop` | save в цикле |
| `T6DatabaseBottlenecksSuite` | `updateEachInLoop` | update в цикле |
| `T6DatabaseBottlenecksSuite` | `saveAllOneByOneWithFlush` | saveAndFlush per item |
| `SyntheticDefectsService` | `t6_unbatched_save_loop` | unbatched save |
| `T6DatabaseBottlenecksSuite` | `unbatchedDelete` | delete в цикле |
| `T6JoinFetchPaginationV2` | `unbatchedDeleteAll` | remove + merge в цикле |
| `T6DatabaseBottlenecksSuite` | `sequentialIndependentQueries` | последовательные независимые запросы |
| `T6DatabaseBottlenecksSuite` | `saveThenFindEach` | save + findById per item |
| `T6JoinFetchPaginationV2` | `sequentialCountThenQuery` | count() + findAll() |
| `T6JoinFetchPaginationV2` | `joinWithoutFetch` | implicit cross join |
| `T6JoinFetchPaginationV2` | `ignoreIndexWithFunction` | `UPPER(s.code)` |
| `T6JoinFetchPaginationV2` | `paginationWithoutCount` | Page без count query |
| `T6JoinFetchPaginationV2` | `loadBlobUnnecessarily` | загрузка noteText |
| `T6JoinFetchPaginationV2` | `readWriteInsteadOfReadOnly` | транзакция read-write |
| `T6JoinFetchPaginationV2` | `selectAllColumnsForSingleField` | SELECT * ради title |

### T7 — Memory Leaks (27 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T7MemoryLeaksSuite` | `growStaticMap` | статический `HashMap` без ограничения |
| `T7MemoryLeaksSuite` | `growConcurrentMap` | статический `ConcurrentHashMap` |
| `T7MemoryLeaksSuite` | `growQueue` | `LinkedList` как unbounded queue |
| `SyntheticDefectsService` | `t7_unbounded_map_leak` | статический Map leak |
| `T7MemoryLeaksSuite` | `growStaticList` | статический `ArrayList` |
| `SyntheticDefectsService` | `t7_retained_list_leak` | статический List leak |
| `T7MemoryLeaksSuite` | `registerListener` | listenerRegistry без remove |
| `T7MemoryLeaksSuite` | `registerCallback` | callbacks без remove |
| `T7MemoryLeaksSuite` | `bufferSessionData` | `sessionBuffer` без очистки |
| `T7MemoryLeaksSuite` | `cacheRequest` | `requestCache` без eviction |
| `T7MemoryLeaksSuite` | `cacheClassMetadata` | `classMetadataCache` без eviction |
| `T7MemoryLeaksSuite` | `appendLog` | `aggregatedLogs` без ограничения |
| `T7MemoryLeaksSuite` | `cacheInThread` | `ThreadLocal` Map без remove |
| `T7MemoryLeaksSuite` | `bufferInThread` | `ThreadLocal` buffer без remove |
| `T7ListenerAndResourceLeakV2` | `leakConnection` | `Connection` не закрыт |
| `T7ListenerAndResourceLeakV2` | `openFileAndForget` | `FileInputStream` не закрыт |
| `T7ListenerAndResourceLeakV2` | `leakResultSet` | ResultSet + Statement + Connection leak |
| `T7ListenerAndResourceLeakV2` | `closeablesNotInFinally` | reader без try-with-resources |
| `T7ListenerAndResourceLeakV2` | `unclosedHttpClientRequest` | async handle утерян |
| `T7ListenerAndResourceLeakV2` | `innerClassLeak` | anonymous `Runnable` держит outer ref |
| `T7ListenerAndResourceLeakV2` | `anonymousClassLeak` | `Consumer<String>` держит `data` |
| `T7ListenerAndResourceLeakV2` | `lambdaLeak` | lambda держит enclosing instance |
| `T7ListenerAndResourceLeakV2` | `addEventListener` | listener никогда не удаляется |
| `T7ListenerAndResourceLeakV2` | `scheduleWithoutCleanup` | `ScheduledFuture` без cancel |
| `T7ListenerAndResourceLeakV2` | `threadWithoutCleanup` | thread не управляется |
| `T7ListenerAndResourceLeakV2` | `growFileHandleCache` | `BYTE_BUFFER_POOL` без ограничения |
| `T7ListenerAndResourceLeakV2` | `cacheByClassLoader` | `CLASSLOADER_CACHE` без eviction |

### T8 — Memory Bloat (25 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T8MemoryBloatSuite` | `filterInMemoryAfterFindAll` | `findAll()` + stream filter |
| `T8MemoryBloatSuite` | `getStationRegionsInMemory` | `findAll()` + map to Set |
| `T8MemoryBloatSuite` | `getAllStationTitles` | `findAll()` + manual list |
| `T8MemoryBloatSuite` | `sumMeasuredByMetricInMemory` | `findAll()` + filter + sum |
| `T8MemoryBloatSuite` | `sortAndLimitInMemory` | `findAll()` + sort + limit |
| `T8MemoryBloatSuite` | `avgMeasuredInMemory` | `findAll()` + ручное avg |
| `T8MemoryBloatSuite` | `countByMetricInMemory` | `findAll()` + ручное count |
| `T8MemoryBloatSuite` | `getAllStationIdsInMemory` | `findAll()` + loop для ID |
| `T8MemoryBloatSuite` | `filterByMetricInMemory` | `findAll()` + filter |
| `T8MemoryBloatSuite` | `filterActiveStationsInMemory` | `findAll()` + filter active |
| `T8MemoryBloatSuite` | `getStationCodeTitleMapInMemory` | `findAll()` + concat |
| `T8MemoryBloatSuite` | `groupByStationInMemory` | `findAll()` + groupingBy |
| `T8StreamingAndProjectionV2` | `fullEntityForSingleField` | full entity для одного поля |
| `T8StreamingAndProjectionV2` | `stationDistinctRegionsInMemory` | `findAll()` + distinct |
| `T8StreamingAndProjectionV2` | `groupByMetricInMemory` | `findAll()` + groupingBy |
| `T8StreamingAndProjectionV2` | `aggregateStatsInMemory` | `findAll()` + ручная статистика |
| `T8StreamingAndProjectionV2` | `multipleLargeCollectionsInMemory` | две коллекции в памяти |
| `T8StreamingAndProjectionV2` | `streamRawSamplesNoPagination` | `findAll()` + filter |
| `T8StreamingAndProjectionV2` | `manualPaginationFindAll` | `findAll()` + subList |
| `SyntheticDefectsService` | `t8_in_memory_filtering` | `findAll()` + filter |
| `T8StreamingAndProjectionV2` | `buildFullCsvInMemory` | CSV в памяти |
| `T8StreamingAndProjectionV2` | `cartesianProductInMemory` | full join в памяти |
| `T8StreamingAndProjectionV2` | `readFileIntoMemory` | файл целиком в `byte[]` |
| `T8StreamingAndProjectionV2` | `readFileIntoString` | файл целиком в строку |
| `T8StreamingAndProjectionV2` | `subListRetainingLargeReference` | `subList(0,10)` держит весь список |

### T9 — CPU Hotspots (26 методов)

| Файл | Метод | Антипаттерн |
|------|-------|-------------|
| `T9ConcurrencyAndLockingV2` | `coarseSynchronizedBlock` | `synchronized(this)` на дешёвые операции |
| `T9CPUHotspotsSuite` | `synchronizedHotString` | `synchronized` на `toUpperCase` |
| `SyntheticDefectsService` | `t9_synchronized_hotspot` | synchronized hotspot |
| `T9ConcurrencyAndLockingV2` | `readLockAcquiredForWrite` | read-lock при write операции |
| `T9ConcurrencyAndLockingV2` | `lockTryLockBusyLoop` | `while(!tryLock())` |
| `T9ConcurrencyAndLockingV2` | `computeHeavyInConcurrentMap` | тяжелый loop внутри `compute` |
| `T9ConcurrencyAndLockingV2` | `exceptionInHotPath` | try/catch на каждый элемент |
| `T9ConcurrencyAndLockingV2` | `streamBoxedOverhead` | `.boxed().mapToDouble(…)` |
| `T9ConcurrencyAndLockingV2` | `systemCurrentTimeInLoop` | `System.currentTimeMillis()` в цикле |
| `T9ConcurrencyAndLockingV2` | `instantNowInLoop` | `Instant.now()` в цикле |
| `T9ConcurrencyAndLockingV2` | `simpleDateFormatInLoop` | `SimpleDateFormat` на каждый вызов |
| `T9CPUHotspotsSuite` | `decimalFormatInLoop` | `DecimalFormat` parse+format в цикле |
| `T9CPUHotspotsSuite` | `stringFormatInLoop` | `String.format` в цикле |
| `T9CPUHotspotsSuite` | `parseDoubleInLoop` | `Double.parseDouble` в цикле |
| `T9CPUHotspotsSuite` | `parseInstantInLoop` | `Instant.from(FORMATTER.parse(…))` в цикле |
| `T9ConcurrencyAndLockingV2` | `bigDecimalInLoop` | `BigDecimal` в цикле |
| `T9ConcurrencyAndLockingV2` | `atomicLongContention` | `atomicCounter.incrementAndGet()` |
| `T9ConcurrencyAndLockingV2` | `stringGetBytesInLoop` | `Arrays.hashCode(s.getBytes())` |
| `T9CPUHotspotsSuite` | `regexCompileInLoop` | `Pattern.compile` в цикле |
| `SyntheticDefectsService` | `t9_regex_compile_in_loop` | `Pattern.compile` 100× |
| `T9CPUHotspotsSuite` | `stringReplaceAllInLoop` | `replaceAll` в цикле |
| `T9CPUHotspotsSuite` | `mathPowInLoop` | `Math.pow` в цикле |
| `T9CPUHotspotsSuite` | `mathSqrtInLoop` | `Math.sqrt` в цикле |
| `T9CPUHotspotsSuite` | `mathLogInLoop` | `Math.log` в цикле |
| `T9CPUHotspotsSuite` | `busyWaitLoop` | tight loop i*i |
| `T9CPUHotspotsSuite` | `reflectionInLoop` | рефлексия в цикле |

### Correct patterns (negative tests) — 112 методов

| Файл | Методов | Что проверяет |
|------|---------|---------------|
| `correct/T1CorrectPatterns` | 13 | StringBuilder, single ops, cached length |
| `correct/T2CorrectPatterns` | 12 | HashSet, HashMap, TreeSet, memoization |
| `correct/T3CorrectPatterns` | 11 | existsBy, count, paginated search |
| `correct/T4CorrectPatterns` | 14 | primitives, array, StringBuilder(capacity) |
| `correct/T5CorrectPatterns` | 15 | single check, switch, Optional.orElse |
| `correct/T6CorrectPatterns` | 13 | saveAll, JOIN FETCH, findAllById |
| `correct/T7CorrectPatterns` | 11 | bounded cache, try-with-resources, listener remove |
| `correct/T8CorrectPatterns` | 11 | pagination, WHERE, findById |
| `correct/T9CorrectPatterns` | 13 | static Pattern, multiply vs pow, tryLock |

### Not-defect patterns (negative tests на утверждения из п.7) — 6 файлов

| Файл | Утверждение п.7 | Что проверяет |
|------|-----------------|---------------|
| `notdefect/NotDefectFieldOrdering` | 1. Порядок полей | BadOrder vs GoodOrder — поля вразнобой vs сгруппированы |
| `notdefect/NotDefectBoundedComplexity` | 2. O(n²) на bounded входе | Nested loops с guard: `MAX_DEVICES_PER_STATION = 8` |
| `notdefect/NotDefectBoundedCache` | 3. Кеш с границей | `LinkedHashMap` с `removeEldestEntry`, `ConcurrentHashMap` с clear |
| `notdefect/NotDefectBoundedCollection` | 4. Коллекция, ограниченная параметром | `maxTopStations=50`, `maxRecentSamples=100` с `Math.min` |
| `notdefect/NotDefectMicrobenchmarkCost` | 5. Микробенчмарк-only стоимость | `Pattern.compile`/`DecimalFormat`/`replaceAll` в cold path (не в hot loop) |
| `notdefect/NotDefectStyleOnly` | 6. Стиль | Allman vs K&R braces, длинные строки, порядок полей/методов |

Эти кейсы автоматически обнаруживаются сканером `gather_non_defect_candidates()` в `patterns.py`
и попадают в LLM-отчёт в секцию **NON-DEFECTS / EXCLUDED BY RULES (SECTION 7)**
с указанием соответствующего правила ND-1…ND-6 и обоснованием, почему это не дефект.
