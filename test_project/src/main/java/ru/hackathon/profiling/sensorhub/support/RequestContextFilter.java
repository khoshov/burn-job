package ru.hackathon.profiling.sensorhub.support;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component("appRequestContextFilter")
@Order(1)
public class RequestContextFilter extends OncePerRequestFilter {

    public static final String HEADER_CORRELATION_ID = "X-Correlation-Id";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String correlationId = request.getHeader(HEADER_CORRELATION_ID);
        if (correlationId == null || correlationId.isBlank()) {
            correlationId = UUID.randomUUID().toString();
        }
        RequestContext.setCorrelationId(correlationId);
        response.setHeader(HEADER_CORRELATION_ID, correlationId);
        try {
            filterChain.doFilter(request, response);
        } finally {
            RequestContext.clear();
        }
    }
}
