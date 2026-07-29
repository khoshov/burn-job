package ru.hackathon.profiling.sensorhub.web.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record MetricTypeUpdateRequest(
        @NotNull @Size(max = 128) String title,
        @NotNull @Size(max = 32) String unitLabel,
        @NotNull @Min(0) @Max(9) Integer scale
) {}
