# 📋 Performance Audit Report — Sandbox

**Target Level:** `hard`  
**Set:** `sandbox`  
**Project:** Java 21 / Spring Boot 3 / Hibernate Performance Audit

---

## 🔍 Executive Summary

This report documents performance bottlenecks identified during automated profiling and static analysis of the sandbox application. The defects have been classified according to the hackathon taxonomy (**T1–T9**) across four primary families: `db`, `memory`, `cpu`, and `algo`.

---

## 🛠️ Detected Performance Issues (`findings`)

### 1. N+1 Query Problem in Department Employee Fetching
* **File:** `src/main/java/com/example/badhibernate/service/NPlusOneService.java` (Lines 27–38)
* **Family:** `db`
* **Taxonomy Codes:** `T6` (Database query inefficiencies), `T2` (Inefficient loop iterations)
* **Mechanism:** Iterating over departments and triggering lazy collection initialization (`department.getEmployees().size()`) causes N secondary `SELECT` statements after the initial `findAll()`.
* **Impact:** 1 + N SQL round-trips over the network.
* **Recommended Fix:** Replace with `JOIN FETCH` JPQL query (`findAllWithEmployeesOptimal()`) to fetch departments and employees in a single SQL statement.
* **Evidence:**
  * Channel: `X-Sql-Count`
  * Before: `101` queries
  * After: `1` query
  * Verification: `GET /api/demo/n-plus-one/bad` vs `GET /api/demo/n-plus-one/good`

---

### 2. In-Memory Filtering & Pagination Stream Bloat
* **File:** `src/main/java/com/example/badhibernate/service/InMemoryFilterService.java` (Lines 29–45)
* **Family:** `memory`
* **Taxonomy Codes:** `T8` (Memory over-allocation), `T3` (Improper function usage)
* **Mechanism:** `orderRepository.findAll()` loads all table records into JVM Heap, applying `.filter()` and `.skip().limit()` via Stream API in RAM instead of database `WHERE` and `LIMIT`.
* **Impact:** Heavy GC pressure and potential `OutOfMemoryError` as dataset grows.
* **Recommended Fix:** Delegate filtering and pagination to PostgreSQL/H2 using Spring Data `Pageable` (`findByStatusOptimal`).
* **Evidence:**
  * Channel: `JVM-Allocated-Memory`
  * Before: `150,000,000` bytes
  * After: `120,000` bytes
  * Verification: `GET /api/demo/in-memory-filter/bad` vs `GET /api/demo/in-memory-filter/good`

---

### 3. Save In Loop Without JDBC Batching
* **File:** `src/main/java/com/example/badhibernate/service/SaveInLoopService.java` (Lines 27–43)
* **Family:** `db`
* **Taxonomy Codes:** `T6` (Database query inefficiencies), `T1` (Redundant computations/operations)
* **Mechanism:** Executing `employeeRepository.save(emp)` in a loop issues N individual JDBC round-trips without batching.
* **Impact:** N network round-trips slowing down bulk insert operations.
* **Recommended Fix:** Accumulate list of entities and invoke `employeeRepository.saveAll(employees)` with JDBC batching enabled.
* **Evidence:**
  * Channel: `Execution-Time-Ms`
  * Before: `450` ms
  * After: `42` ms
  * Verification: `POST /api/demo/save-in-loop/compare?count=200`

---

### 4. Full Entity Fetching for Lightweight DTO Projections
* **File:** `src/main/java/com/example/badhibernate/service/FullEntityFetchService.java` (Lines 26–32)
* **Family:** `memory`
* **Taxonomy Codes:** `T3` (Improper function usage), `T4` (Data layout inefficiencies)
* **Mechanism:** Loading managed `@Entity` instances along with heavy `@Lob` columns (`detailedBiography`) when only scalar fields (`firstName`, `email`) are required.
* **Impact:** Excessive memory footprint and overhead in Hibernate 1st-level cache (`PersistenceContext`).
* **Recommended Fix:** Use Spring Data JPA Interface Projections (`EmployeeSimpleProjection`).
* **Evidence:**
  * Channel: `Selected-Columns-Byte-Size`
  * Before: `409,600` bytes
  * After: `8,192` bytes
  * Verification: `GET /api/demo/entity-fetch/bad` vs `GET /api/demo/entity-fetch/good`

---

## 🛡️ Checked Non-Defects (`checked_but_not_an_issue`)

Per Section 7 of coding standards, the following areas were inspected and explicitly determined **not** to be defects:

1. **Employee Field Ordering (`Employee.java`)**
   * *Claim:* Field declaration order in entity class looks unoptimized.
   * *Justification:* JOL (Java Object Layout) inspection showed object size remains identical (40 bytes) due to HotSpot JVM automatic field reordering.
2. **InMemoryFilterService Small List Matching**
   * *Claim:* Quadratic complexity matching statuses for small inputs.
   * *Justification:* Input size is bounded by API contract (`pageSize <= 8`), executing in sub-microsecond time.
3. **Reference Cache Size (`CacheConfig.java`)**
   * *Claim:* Reference lookup cache grows in memory.
   * *Justification:* Cache is configured with maximum bounded size (`maxSize`) and LRU eviction policy.
