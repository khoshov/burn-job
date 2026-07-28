package com.example.badhibernate.service;

import com.example.badhibernate.dto.OrderSummaryDto;
import com.example.badhibernate.entity.Order;
import com.example.badhibernate.repository.OrderRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class InMemoryFilterService {

    private final OrderRepository orderRepository;

    public InMemoryFilterService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    /**
     * ANTIPATTERN (SubOptimal): Loads all order records into JVM Heap and filters via Stream API.
     */
    @Transactional(readOnly = true)
    public List<OrderSummaryDto> getOrdersByStatusSubOptimal(String status, int page, int size) {
        List<Order> allOrders = orderRepository.findAll();
        return allOrders.stream()
                .filter(o -> status.equalsIgnoreCase(o.getStatus()))
                .skip((long) page * size)
                .limit(size)
                .map(o -> new OrderSummaryDto(o.getId(), o.getOrderNumber(), o.getCustomerEmail(), o.getStatus(), o.getCreatedAt(), o.getTotalAmount()))
                .toList();
    }

    /**
     * FIX VARIANT 8.1: Pageable with Page (Includes total count query)
     */
    @Transactional(readOnly = true)
    public List<OrderSummaryDto> getOrdersVariant1_Pageable(String status, int page, int size) {
        return orderRepository.findByStatusOptimal(status, PageRequest.of(page, size)).getContent();
    }

    /**
     * FIX VARIANT 3.3 / 8.1: Slice Pagination (Eliminates total COUNT(*) query)
     */
    @Transactional(readOnly = true)
    public List<OrderSummaryDto> getOrdersVariant2_Slice(String status, int page, int size) {
        return orderRepository.findByStatusSlice(status, PageRequest.of(page, size)).getContent();
    }

    /**
     * FIX VARIANT 8.2: Keyset / Seek Cursor Pagination
     */
    @Transactional(readOnly = true)
    public List<OrderSummaryDto> getOrdersVariant3_Keyset(String status, long lastSeenId, int size) {
        return orderRepository.findByStatusKeyset(status, lastSeenId, PageRequest.of(0, size));
    }

    /**
     * OPTIMAL FIX: Uses Spring Data Pageable.
     */
    @Transactional(readOnly = true)
    public Page<OrderSummaryDto> getOrdersByStatusOptimal(String status, int page, int size) {
        return orderRepository.findByStatusOptimal(status, PageRequest.of(page, size));
    }

    /**
     * Feature Toggle Router for In-Memory Filter Fix Variants.
     */
    @Transactional(readOnly = true)
    public List<OrderSummaryDto> getOrdersByVariant(String status, int page, int size, String variant) {
        if (variant == null) variant = "v1";
        return switch (variant.toLowerCase()) {
            case "v1", "pageable" -> getOrdersVariant1_Pageable(status, page, size);
            case "v2", "slice" -> getOrdersVariant2_Slice(status, page, size);
            case "v3", "keyset" -> getOrdersVariant3_Keyset(status, 0L, size);
            case "suboptimal", "bad" -> getOrdersByStatusSubOptimal(status, page, size);
            default -> getOrdersVariant1_Pageable(status, page, size);
        };
    }
}