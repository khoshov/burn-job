package ru.hackathon.profiling.sensorhub.web.dto;

public record OverviewDto(
        long samples,
        Double avgMeasured,
        Double maxMeasured
) {}
