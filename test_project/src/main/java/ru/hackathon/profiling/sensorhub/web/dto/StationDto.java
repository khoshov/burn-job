package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.LocalDate;

public record StationDto(
        String code,
        String title,
        String region,
        boolean active,
        LocalDate installedOn
) {}
