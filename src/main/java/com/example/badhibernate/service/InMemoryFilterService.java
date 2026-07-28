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
     * OPTIMIZED: Pushes WHERE filtering and pagination to Database via PageRequest.
     * Eliminates loading all records into JVM heap memory.
     */
    @Transactional(readOnly = true)
    public List<OrderSummaryDto> getOrdersByStatusSubOptimal(String status, int page, int size) {
        return orderRepository.findByStatusOptimal(status, PageRequest.of(page, size))
                .getContent();
    }

    /**
     * OPTIMAL FIX: Delegates filtering and pagination directly to the database via SQL WHERE and LIMIT/OFFSET clauses.
     */
    @Transactional(readOnly = true)
    public Page<OrderSummaryDto> getOrdersByStatusOptimal(String status, int page, int size) {
        return orderRepository.findByStatusOptimal(status, PageRequest.of(page, size));
    }
}