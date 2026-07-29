package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.Instant;

public record SnapshotDto(
        String key,
        String digest,
        long payloadSize,
        Instant builtAt
) {}
