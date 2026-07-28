package com.example.badhibernate.repository;

import com.example.badhibernate.dto.OrderSummaryDto;
import com.example.badhibernate.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OrderRepository extends JpaRepository<Order, Long> {

    // Optimal database-level search and pagination
    @Query("SELECT new com.example.badhibernate.dto.OrderSummaryDto(o.id, o.orderNumber, o.customerEmail, o.status, o.createdAt, o.totalAmount) " +
           "FROM Order o WHERE o.status = :status")
    Page<OrderSummaryDto> findByStatusOptimal(@Param("status") String status, Pageable pageable);
}
