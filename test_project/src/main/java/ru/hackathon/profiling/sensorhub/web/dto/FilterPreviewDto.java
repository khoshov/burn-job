package ru.hackathon.profiling.sensorhub.web.dto;

import java.util.List;

public record FilterPreviewDto(
        List<String> pairs,
        int count
) {}
