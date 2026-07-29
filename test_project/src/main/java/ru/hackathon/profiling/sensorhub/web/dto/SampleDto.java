package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.Instant;

public record SampleDto(
        Long id,
        String stationCode,
        String metricCode,
        Double measured,
        Instant takenAt,
        String quality,
        String badge
) {}
