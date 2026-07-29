package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.LocalDate;
import java.util.List;

public record StationStatsDto(
        String stationCode,
        LocalDate from,
        LocalDate to,
        List<StationStatsRowDto> rows,
        StationStatsTotalsDto totals
) {
    public record StationStatsRowDto(
            String metricCode,
            LocalDate day,
            long samples,
            Double avgMeasured
    ) {}

    public record StationStatsTotalsDto(
            long samples,
            Double avgMeasured
    ) {}
}
