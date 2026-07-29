package ru.hackathon.profiling.sensorhub.web.dto;

public record ErrorDto(
        String code,
        String message,
        String correlationId
) {}
