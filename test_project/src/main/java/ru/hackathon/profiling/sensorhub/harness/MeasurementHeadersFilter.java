package ru.hackathon.profiling.sensorhub.harness;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@Order(2)
public class MeasurementHeadersFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        SqlCounter.reset();
        try {
            filterChain.doFilter(request, response);
        } finally {
            long count = SqlCounter.getCount();
            long elapsed = SqlCounter.getElapsedMs();
            response.setHeader("X-Sql-Count", String.valueOf(count));
            response.setHeader("X-Elapsed-Ms", String.valueOf(elapsed));
            SqlCounter.clear();
        }
    }
}
