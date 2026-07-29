package ru.hackathon.profiling.sensorhub.web.dto;

public record MetricTypeDto(
        String code,
        String title,
        String unitLabel,
        Integer scale
) {}
