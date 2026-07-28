package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T8]
 * Bottleneck: In-memory stream filtering and full heap pagination bloat
 * Original file (T8_MemoryBloatExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T8_MemoryBloatExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t8_memory_bloat;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * ✅ Fix 1: Database-Level Pagination with Spring Data JPA
 * Transfers LIMIT/OFFSET to the database, eliminating heap bloat entirely.
 */
@Service
public class T8_DatabasePaginationFix {

    @Repository
    public interface OrderRepository extends JpaRepository<OrderEntity, Long> {
        
        @Query("SELECT o FROM OrderEntity o WHERE o.status = :status ORDER BY o.id")
        Page<OrderEntity> findByStatusWithPagination(
                @Param("status") String status, 
                PageRequest pageRequest);
    }

    private final OrderRepository orderRepository;

    public T8_DatabasePaginationFix(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    /**
     * Fetches only the requested page from the database.
     * Memory usage: O(pageSize) instead of O(totalRows)
     */
    public List<OrderEntity> getOrdersPage(String status, int page, int size) {
        PageRequest pageRequest = PageRequest.of(page, size);
        Page<OrderEntity> orderPage = orderRepository.findByStatusWithPagination(status, pageRequest);
        return orderPage.getContent();
    }
}

// Supporting entity (would normally be in its own file)
@Entity
@Table(name = "orders")
class OrderEntity {
    @Id
    private Long id;
    private String status;
    private String description;
    // getters, setters, constructors omitted for brevity
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t8_memory_bloat;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

/**
 * ✅ Fix 2: Cursor-Based (Keyset) Pagination
 * Uses the last seen ID as a cursor instead of OFFSET.
 * More efficient for deep pagination and large datasets.
 */
public class T8_CursorPaginationFix {

    private final String jdbcUrl;
    private final String username;
    private final String password;

    public T8_CursorPaginationFix(String jdbcUrl, String username, String password) {
        this.jdbcUrl = jdbcUrl;
        this.username = username;
        this.password = password;
    }

    /**
     * Fetches the next page of results after the given cursor.
     * 
     * @param lastSeenId The ID of the last record from the previous page (0 for first page)
     * @param size       Number of records to fetch
     * @return List of records for the current page
     */
    public List<String> getOrdersPageAfterCursor(long lastSeenId, int size) {
        String sql = "SELECT id, data FROM orders WHERE id > ? ORDER BY id LIMIT ?";
        List<String> results = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(jdbcUrl, username, password);
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setLong(1, lastSeenId);
            stmt.setInt(2, size);
            
            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    results.add(rs.getString("data"));
                }
            }
        } catch (SQLException e) {
            throw new RuntimeException("Database error during cursor pagination", e);
        }
        
        return results;
    }

    /**
     * Convenience method for first page (no cursor needed)
     */
    public List<String> getFirstPage(int size) {
        return getOrdersPageAfterCursor(0L, size);
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t8_memory_bloat;

import io.r2dbc.spi.ConnectionFactory;
import org.springframework.data.r2dbc.core.R2dbcEntityTemplate;
import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.repository.reactive.ReactiveCrudRepository;
import org.springframework.stereotype.Repository;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * ✅ Fix 3: Reactive Streaming with Backpressure
 * Streams data from database to client without heap accumulation.
 * Ideal for large exports or real-time processing.
 */
@Service
public class T8_ReactiveStreamingFix {

    @Repository
    public interface ReactiveOrderRepository extends ReactiveCrudRepository<OrderReactive, Long> {
        
        @Query("SELECT * FROM orders WHERE status = :status ORDER BY id")
        Flux<OrderReactive> findByStatusStreaming(String status);
    }

    private final ReactiveOrderRepository orderRepository;
    private final R2dbcEntityTemplate entityTemplate;

    public T8_ReactiveStreamingFix(
            ReactiveOrderRepository orderRepository,
            ConnectionFactory connectionFactory) {
        this.orderRepository = orderRepository;
        this.entityTemplate = new R2dbcEntityTemplate(connectionFactory);
    }

    /**
     * Streams orders reactively with controlled batch size.
     * Memory usage: O(batchSize) regardless of total dataset size.
     */
    public Flux<OrderReactive> streamOrders(String status, int batchSize) {
        return orderRepository.findByStatusStreaming(status)
                .buffer(batchSize)  // Process in batches for efficiency
                .flatMap(batch -> {
                    // Process each batch (e.g., write to file, send to client)
                    return Flux.fromIterable(batch);
                });
    }

    /**
     * Alternative: Manual cursor-based reactive streaming for more control
     */
    public Flux<OrderReactive> streamOrdersWithCursor(String status, int batchSize) {
        return Flux.generate(
                () -> new CursorState(0L, true),
                (state, sink) -> {
                    if (!state.hasMore) {
                        sink.complete();
                        return state;
                    }
                    
                    return entityTemplate.select(OrderReactive.class)
                            .from("orders")
                            .matching(org.springframework.data.relational.core.query.Query.query(
                                    org.springframework.data.relational.core.query.Criteria.where("status").is(status)
                                            .and(org.springframework.data.relational.core.query.Criteria.where("id").greaterThan(state.lastId))
                            ).sort(org.springframework.data.relational.core.query.Sort.by("id")).limit(batchSize))
                            .all()
                            .collectList()
                            .flatMapMany(Flux::fromIterable)
                            .doOnNext(order -> {
                                sink.next(order);
                                state.lastId = order.getId();
                            })
                            .doOnComplete(() -> {
                                // If we got fewer results than batchSize, we're done
                                state.hasMore = false;
                            })
                            .then(Mono.just(state))
                            .block();
                }
        );
    }

    // Internal state class for cursor tracking
    private static class CursorState {
        long lastId;
        boolean hasMore;

        CursorState(long lastId, boolean hasMore) {
            this.lastId = lastId;
            this.hasMore = hasMore;
        }
    }
}

// Supporting reactive entity
@Table("orders")
class OrderReactive {
    @Id
    private Long id;
    private String status;
    private String data;
    // getters, setters, constructors omitted for brevity
}
    */

}
