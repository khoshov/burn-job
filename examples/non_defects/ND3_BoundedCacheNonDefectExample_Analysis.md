# Section 7 Non-Defect Analysis: [ND-3] Кэш с заданной границей и политикой вытеснения

- **Target File:** `ND3_BoundedCacheNonDefectExample.java`
- **Classification Status:** 🟢 `NON_DEFECT` (DO NOT REFACTOR)
- **Rule ID:** `NON_DEFECT_BOUNDED_CACHE`

## 📋 Rule Summary & Mechanism
Рост размера кеша до сконфигурированного лимита (maxSize / Eviction) является проектным поведением, а не утечкой памяти.

## 🛡️ Rationale for Zero Mutation
1. **JVM / HotSpot Optimization:** The behavior is handled automatically by the runtime or bounded by contract.
2. **Required Evidence:** Configured eviction policy (LRU/LFU/Caffeine maxSize) or bounded limit.
3. **Conclusion:** Code refactoring would yield zero runtime benefit and is excluded under project performance rules.
