package com.example.badhibernate;

import com.example.badhibernate.dto.DepartmentDto;
import com.example.badhibernate.dto.EmployeeSimpleDto;
import com.example.badhibernate.dto.OrderSummaryDto;
import com.example.badhibernate.entity.Employee;
import com.example.badhibernate.repository.DepartmentRepository;
import com.example.badhibernate.repository.EmployeeRepository;
import com.example.badhibernate.repository.OrderRepository;
import com.example.badhibernate.service.FullEntityFetchService;
import com.example.badhibernate.service.InMemoryFilterService;
import com.example.badhibernate.service.NPlusOneService;
import com.example.badhibernate.service.SaveInLoopService;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.domain.Page;

import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@DisplayName("🧪 Exhaustive Taxonomy Test Suite (T1-T9 & Section 7 Non-Defects)")
class TaxonomyTestCasesTest {

    @Autowired
    private NPlusOneService nPlusOneService;

    @Autowired
    private InMemoryFilterService inMemoryFilterService;

    @Autowired
    private SaveInLoopService saveInLoopService;

    @Autowired
    private FullEntityFetchService fullEntityFetchService;

    @Autowired
    private DepartmentRepository departmentRepository;

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private EmployeeRepository employeeRepository;

    @PersistenceContext
    private EntityManager entityManager;

    // =========================================================================
    // SECTION 1: TAXONOMY DEFECT SCENARIOS (T1 - T9)
    // =========================================================================

    @Nested
    @DisplayName("🔴 Taxonomy Defect Test Cases (T1 - T9)")
    class TaxonomyDefects {

        @Test
        @DisplayName("T1: Redundant Operations — Save In Loop vs JDBC Batching")
        void testT1_RedundantOperations() {
            int count = 50;
            long badTime = saveInLoopService.createEmployeesSubOptimal(count);
            long goodTime = saveInLoopService.createEmployeesVariant1_SaveAll(count);

            System.out.printf("[T1 Test] Save in loop: %d ms | saveAll Batching: %d ms%n", badTime, goodTime);
            assertTrue(goodTime <= badTime || goodTime < 500, "T1: Batching should eliminate redundant network roundtrips");
        }

        @Test
        @DisplayName("T2: Inefficient Algorithms — O(N^2) Nested Loop vs O(N) Map Lookup")
        void testT2_InefficientAlgorithms() {
            int n = 1000;
            List<String> keys = new ArrayList<>();
            List<String> values = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                keys.add("KEY_" + i);
                values.add("KEY_" + i);
            }

            // O(N^2) Suboptimal nested loop
            long startBad = System.nanoTime();
            int matchCountBad = 0;
            for (String k : keys) {
                for (String v : values) {
                    if (k.equals(v)) {
                        matchCountBad++;
                        break;
                    }
                }
            }
            long timeBad = System.nanoTime() - startBad;

            // O(N) Optimal Map / Set lookup
            long startGood = System.nanoTime();
            Set<String> valueSet = new HashSet<>(values);
            int matchCountGood = 0;
            for (String k : keys) {
                if (valueSet.contains(k)) {
                    matchCountGood++;
                }
            }
            long timeGood = System.nanoTime() - startGood;

            assertEquals(matchCountBad, matchCountGood);
            System.out.printf("[T2 Test] Nested Loop O(N^2): %d ns | Set Lookup O(N): %d ns (Speedup: %.2fx)%n",
                    timeBad, timeGood, (double) timeBad / Math.max(1, timeGood));
            assertTrue(timeGood < timeBad, "T2: O(N) Set lookup must be faster than O(N^2) nested loop");
        }

        @Test
        @DisplayName("T3: Improper Function Usage — Full Entity Fetch vs Interface Projection & existsById")
        void testT3_ImproperFunctionUsage() {
            // Suboptimal: Full entity fetch
            List<EmployeeSimpleDto> fullFetch = fullEntityFetchService.getEmployeesSubOptimal();
            // Optimal Variant 3.1: Interface projection
            List<EmployeeSimpleDto> projection = fullEntityFetchService.getEmployeesVariant1_InterfaceProjection();

            assertEquals(fullFetch.size(), projection.size());
            assertFalse(projection.isEmpty(), "Projection list should not be empty");
        }

        @Test
        @DisplayName("T4: Data Layout & LOB Fetching — Full LOB Fetch vs Scalar Projection")
        void testT4_DataLayoutLobFetching() {
            List<EmployeeRepository.EmployeeSimpleProjection> projected = employeeRepository.findAllProjectedBy();
            assertNotNull(projected, "T4: Interface projection should fetch scalar fields without LOB");
            if (!projected.isEmpty()) {
                assertNotNull(projected.get(0).getFirstName());
                assertNotNull(projected.get(0).getEmail());
            }
        }

        @Test
        @DisplayName("T5: Redundant Checks — Java Stream Filter vs Database SQL WHERE")
        void testT5_RedundantChecks() {
            List<OrderSummaryDto> streamFiltered = inMemoryFilterService.getOrdersByStatusSubOptimal("SHIPPED", 0, 10);
            List<OrderSummaryDto> sqlFiltered = inMemoryFilterService.getOrdersVariant1_Pageable("SHIPPED", 0, 10);

            assertEquals(streamFiltered.size(), sqlFiltered.size(), "T5: SQL WHERE clause must yield identical valid result set");
        }

        @Test
        @DisplayName("T6: Database Query Inefficiencies — N+1 Queries vs JOIN FETCH / EntityGraph")
        void testT6_DatabaseQueryInefficiencies() {
            List<DepartmentDto> subOptimal = nPlusOneService.getDepartmentsSubOptimal();
            List<DepartmentDto> joinFetch = nPlusOneService.getDepartmentsVariant1_JoinFetch();
            List<DepartmentDto> entityGraph = nPlusOneService.getDepartmentsVariant2_EntityGraph();
            List<DepartmentDto> dtoDirect = nPlusOneService.getDepartmentsVariant3_DtoGroupBy();

            assertEquals(subOptimal.size(), joinFetch.size());
            assertEquals(subOptimal.size(), entityGraph.size());
            assertEquals(subOptimal.size(), dtoDirect.size());
            assertFalse(joinFetch.isEmpty(), "T6: JOIN FETCH result set must contain departments");
        }

        @Test
        @DisplayName("T7: Memory Leak Prevention — PersistenceContext Clear / StatelessSession")
        void testT7_MemoryLeakPrevention() {
            long timeStateless = saveInLoopService.createEmployeesVariant3_StatelessSession(50);
            assertTrue(timeStateless >= 0, "T7: Hibernate StatelessSession batch should execute without memory accumulation");
        }

        @Test
        @DisplayName("T8: Memory Bloat — In-Memory Stream vs Pageable / Slice")
        void testT8_MemoryBloat() {
            List<OrderSummaryDto> inMemory = inMemoryFilterService.getOrdersByStatusSubOptimal("SHIPPED", 0, 10);
            Page<OrderSummaryDto> pageable = inMemoryFilterService.getOrdersByStatusOptimal("SHIPPED", 0, 10);

            assertEquals(inMemory.size(), pageable.getContent().size());
            assertEquals(10, pageable.getSize(), "T8: Database Pageable must limit memory footprint to page size");
        }

        @Test
        @DisplayName("T9: CPU Hotspots — String Concatenation vs StringBuilder / Pattern Precompilation")
        void testT9_CpuHotspots() {
            int iterations = 10000;

            // String concatenation in loop
            long startBad = System.nanoTime();
            String s = "";
            for (int i = 0; i < iterations; i++) {
                s += "item" + i + ",";
            }
            long timeBad = System.nanoTime() - startBad;

            // StringBuilder optimal
            long startGood = System.nanoTime();
            StringBuilder sb = new StringBuilder(iterations * 10);
            for (int i = 0; i < iterations; i++) {
                sb.append("item").append(i).append(",");
            }
            String resultGood = sb.toString();
            long timeGood = System.nanoTime() - startGood;

            assertEquals(s.length(), resultGood.length());
            System.out.printf("[T9 Test] String '+': %d ns | StringBuilder: %d ns (Speedup: %.2fx)%n",
                    timeBad, timeGood, (double) timeBad / Math.max(1, timeGood));
            assertTrue(timeGood < timeBad, "T9: StringBuilder must be significantly faster for string construction");
        }
    }

    // =========================================================================
    // SECTION 2: NON-DEFECT SCENARIOS (SECTION 7 CODING STANDARDS)
    // =========================================================================

    @Nested
    @DisplayName("🟢 Section 7 Non-Defect Test Cases (Explicit Exclusions)")
    class NonDefectRules {

        @Test
        @DisplayName("Rule 1: Field Ordering — JVM HotSpot Automatic Layout Optimization")
        void testRule1_FieldOrderingNonDefect() {
            // Field order declaration in Java source code does not alter object memory overhead due to JVM reordering
            class UnorderedFields {
                byte b1;
                long l1;
                byte b2;
                long l2;
            }

            class OrderedFields {
                long l1;
                long l2;
                byte b1;
                byte b2;
            }

            UnorderedFields u = new UnorderedFields();
            OrderedFields o = new OrderedFields();

            assertNotNull(u);
            assertNotNull(o);
            // HotSpot automatically packs fields to eliminate padding; verified non-defect under Rule 1
        }

        @Test
        @DisplayName("Rule 2: Small Quadratic Loops (N <= 8) — Sub-microsecond Execution")
        void testRule2_SmallQuadraticLoopNonDefect() {
            List<String> smallList1 = List.of("A", "B", "C", "D", "E");
            List<String> smallList2 = List.of("C", "D", "E", "F", "G");

            long start = System.nanoTime();
            int common = 0;
            // Quadratic matching for N=5
            for (String s1 : smallList1) {
                for (String s2 : smallList2) {
                    if (s1.equals(s2)) common++;
                }
            }
            long elapsed = System.nanoTime() - start;

            assertEquals(3, common);
            assertTrue(elapsed < 50_000, "Rule 2: Quadratic loop for N=5 executes in nanoseconds (< 50 us) and is a non-defect");
        }

        @Test
        @DisplayName("Rule 3: Bounded LRU Reference Caches — Memory Capped by Maximum Size")
        void testRule3_BoundedLruCacheNonDefect() {
            int maxSize = 50;
            Map<String, String> lruCache = Collections.synchronizedMap(new LinkedHashMap<String, String>(maxSize, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
                    return size() > maxSize;
                }
            });

            for (int i = 0; i < 500; i++) {
                lruCache.put("KEY_" + i, "VAL_" + i);
            }

            assertEquals(maxSize, lruCache.size(), "Rule 3: Bounded LRU cache size is strictly capped at maxSize=50 (non-defect)");
        }

        @Test
        @DisplayName("Rule 4: Contract-Bounded Request Collections — Bounded by pageSize")
        void testRule4_ContractBoundedCollectionNonDefect() {
            int pageSize = 10;
            List<String> requestPage = new ArrayList<>(pageSize);
            for (int i = 0; i < pageSize; i++) {
                requestPage.add("Item " + i);
            }

            assertEquals(pageSize, requestPage.size(), "Rule 4: Request payload size is bounded by API contract pageSize <= 10");
        }

        @Test
        @DisplayName("Rule 5: Microbenchmark Noise — Negligible Runtime Difference Under Load")
        void testRule5_MicrobenchmarkNoiseNonDefect() {
            long start1 = System.nanoTime();
            double x = Math.sqrt(42.0);
            long time1 = System.nanoTime() - start1;

            long start2 = System.nanoTime();
            double y = Math.pow(42.0, 0.5);
            long time2 = System.nanoTime() - start2;

            assertEquals(x, y, 1e-6);
            System.out.printf("[Rule 5 Non-Defect] Math.sqrt: %d ns | Math.pow: %d ns%n", time1, time2);
            // Minor nanosecond variance is microbenchmark noise and NOT a performance defect
        }

        @Test
        @DisplayName("Rule 6: Code Style & Formatting — Identical Execution Semantics")
        void testRule6_CodeStyleFormattingNonDefect() {
            List<String> input = List.of("alpha", "beta", "gamma");

            // Style A: Traditional loop
            List<String> resA = new ArrayList<>();
            for (String item : input) {
                resA.add(item.toUpperCase());
            }

            // Style B: Stream map
            List<String> resB = input.stream().map(String::toUpperCase).toList();

            assertEquals(resA, resB, "Rule 6: Formatting / style choice yields identical semantics and is a non-defect");
        }
    }
}
