package ru.hackathon.profiling.sensorhub.web.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.LocalDate;

public record StationCreateRequest(
        @NotNull @Size(max = 32) String code,
        @NotNull @Size(max = 128) String title,
        @NotNull @Size(max = 64) String region,
        @NotNull LocalDate installedOn
) {}
