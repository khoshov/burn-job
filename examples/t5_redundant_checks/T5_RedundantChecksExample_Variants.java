package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T5]
 * Bottleneck: Duplicate in-memory validation filtering in Java Stream
 * Original file (T5_RedundantChecksExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T5_RedundantChecksExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t5_redundant_checks;

import java.util.List;

/**
 * ✅ Variant 1: Repository-Level SQL Delegation
 * Moves filtering to the database via a dedicated repository method.
 */
public class T5_RedundantChecksExample {

    public record Order(Long id, String status) {}

    // Simulated repository interface
    public interface OrderRepository {
        List<Order> findAllByStatus(String status);
    }

    private final OrderRepository orderRepository;

    public T5_RedundantChecksExample(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    // ✅ Optimal: Database handles filtering via WHERE clause
    public List<Order> filterByStatus(String targetStatus) {
        return orderRepository.findAllByStatus(targetStatus);
    }
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t5_redundant_checks;

import java.util.*;
import java.util.stream.Collector;
import java.util.stream.Collectors;

/**
 * ✅ Variant 2: Lazy Evaluation with Custom Collector
 * Optimizes in-memory filtering by pre-grouping data once.
 */
public class T5_RedundantChecksExample {

    public record Order(Long id, String status) {}

    // Pre-grouped cache to avoid repeated filtering
    private Map<String, List<Order>> ordersByStatus = new HashMap<>();

    // ✅ Optimal: Group once, retrieve instantly
    public List<Order> filterByStatusCached(List<Order> allOrdersFromDb, String targetStatus) {
        if (ordersByStatus.isEmpty()) {
            ordersByStatus = allOrdersFromDb.stream()
                    .collect(Collectors.groupingBy(Order::status));
        }
        return ordersByStatus.getOrDefault(targetStatus, Collections.emptyList());
    }

    // Alternative: Custom collector for single-use optimization
    public List<Order> filterByStatusCustomCollector(List<Order> allOrdersFromDb, String targetStatus) {
        return allOrdersFromDb.stream()
                .collect(Collector.of(
                        ArrayList::new,
                        (list, order) -> {
                            if (targetStatus.equals(order.status())) {
                                list.add(order);
                            }
                        },
                        (left, right) -> {
                            left.addAll(right);
                            return left;
                        }
                ));
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t5_redundant_checks;

import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * ✅ Variant 3: Parallel Processing with Predicate Factory
 * Optimizes in-memory filtering using parallel streams and predicate caching.
 */
public class T5_RedundantChecksExample {

    public record Order(Long id, String status) {}

    // Cache compiled predicates for reuse
    private static final ConcurrentMap<String, Predicate<Order>> PREDICATE_CACHE = new ConcurrentHashMap<>();

    // ✅ Optimal: Parallel processing with cached predicates
    public List<Order> filterByStatusParallel(List<Order> allOrdersFromDb, String targetStatus) {
        // Threshold check: if dataset is small, use sequential; otherwise parallel
        if (allOrdersFromDb.size() < 1000) {
            return filterSequential(allOrdersFromDb, targetStatus);
        }

        Predicate<Order> predicate = PREDICATE_CACHE.computeIfAbsent(
                targetStatus,
                status -> order -> status.equals(order.status())
        );

        return allOrdersFromDb.parallelStream()
                .filter(predicate)
                .collect(Collectors.toList());
    }

    // Fallback for small datasets
    private List<Order> filterSequential(List<Order> allOrdersFromDb, String targetStatus) {
        return allOrdersFromDb.stream()
                .filter(order -> targetStatus.equals(order.status()))
                .collect(Collectors.toList());
    }

    // ✅ Intelligent fallback: detect when DB filtering would be better
    public List<Order> filterWithFallback(List<Order> allOrdersFromDb, String targetStatus) {
        // If we're filtering out more than 80% of data, warn (simulated)
        long totalCount = allOrdersFromDb.size();
        List<Order> filtered = filterByStatusParallel(allOrdersFromDb, targetStatus);

        if (totalCount > 10000 && filtered.size() < totalCount * 0.2) {
            System.err.println("⚠️ Warning: Heavy filtering detected. Consider moving to SQL WHERE clause.");
        }

        return filtered;
    }
}
    */

}
