package ru.hackathon.profiling.sensorhub.web.dto;

public record ImportErrorDto(
        int line,
        String code,
        String message
) {}
