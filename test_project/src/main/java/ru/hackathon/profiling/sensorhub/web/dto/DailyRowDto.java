package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.LocalDate;

public record DailyRowDto(
        LocalDate day,
        String stationCode,
        long samples,
        Double avgMeasured,
        Double maxMeasured
) {}
