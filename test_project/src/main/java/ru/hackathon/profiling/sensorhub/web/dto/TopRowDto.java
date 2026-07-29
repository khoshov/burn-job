package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.Instant;

public record TopRowDto(
        String stationCode,
        String metricCode,
        Double measured,
        Instant takenAt
) {}
