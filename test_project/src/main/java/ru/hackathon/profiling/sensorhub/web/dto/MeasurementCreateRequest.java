package ru.hackathon.profiling.sensorhub.web.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;

public record MeasurementCreateRequest(
        @NotNull @Valid List<MeasurementItemDto> items
) {
    public static final int MAX_ITEMS = 200;
}
