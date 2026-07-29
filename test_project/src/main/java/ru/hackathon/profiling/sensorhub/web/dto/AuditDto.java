package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.Instant;

public record AuditDto(
        String path,
        String httpMethod,
        int statusCode,
        long elapsedMs,
        Instant loggedAt,
        String correlationId
) {}
