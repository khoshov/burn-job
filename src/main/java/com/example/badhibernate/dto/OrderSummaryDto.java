package com.example.badhibernate.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record OrderSummaryDto(
        Long id,
        String orderNumber,
        String customerEmail,
        String status,
        LocalDateTime createdAt,
        BigDecimal totalAmount
) {}
