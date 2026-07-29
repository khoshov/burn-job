package ru.hackathon.profiling.sensorhub.web.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.Instant;

public record MeasurementItemDto(
        @NotNull @Size(max = 32) String stationCode,
        @NotNull @Size(max = 32) String metricCode,
        @NotNull Double measured,
        @NotNull Instant takenAt,
        Integer qualityFlag
) {}
