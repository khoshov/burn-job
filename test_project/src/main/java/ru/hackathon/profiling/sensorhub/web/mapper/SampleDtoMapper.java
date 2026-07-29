package ru.hackathon.profiling.sensorhub.web.mapper;

import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.web.dto.SampleDto;

public class SampleDtoMapper {

    public static SampleDto toDto(RawSample sample, String stationCode) {
        String quality = sample.getQuality() != null ? sample.getQuality() : "GOOD";
        String badge = QualityBadgeFormatter.formatBadge(quality);
        return new SampleDto(
                sample.getId(),
                stationCode,
                sample.getMetricCode(),
                sample.getMeasured(),
                sample.getTakenAt(),
                quality,
                badge
        );
    }
}
