package com.example.badhibernate.repository;

import com.example.badhibernate.dto.OrderSummaryDto;
import com.example.badhibernate.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {

    // Variant 1: Database-level Pageable search with Page (returns total count)
    @Query("SELECT new com.example.badhibernate.dto.OrderSummaryDto(o.id, o.orderNumber, o.customerEmail, o.status, o.createdAt, o.totalAmount) " +
           "FROM Order o WHERE o.status = :status")
    Page<OrderSummaryDto> findByStatusOptimal(@Param("status") String status, Pageable pageable);

    // Variant 2: Slice pagination without total COUNT(*) query
    @Query("SELECT new com.example.badhibernate.dto.OrderSummaryDto(o.id, o.orderNumber, o.customerEmail, o.status, o.createdAt, o.totalAmount) " +
           "FROM Order o WHERE o.status = :status")
    Slice<OrderSummaryDto> findByStatusSlice(@Param("status") String status, Pageable pageable);

    // Variant 3: Keyset / Seek pagination by ID
    @Query("SELECT new com.example.badhibernate.dto.OrderSummaryDto(o.id, o.orderNumber, o.customerEmail, o.status, o.createdAt, o.totalAmount) " +
           "FROM Order o WHERE o.status = :status AND o.id > :lastSeenId ORDER BY o.id ASC")
    List<OrderSummaryDto> findByStatusKeyset(@Param("status") String status, @Param("lastSeenId") Long lastSeenId, Pageable pageable);
}

