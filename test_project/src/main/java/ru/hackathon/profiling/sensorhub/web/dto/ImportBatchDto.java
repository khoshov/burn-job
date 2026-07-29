package ru.hackathon.profiling.sensorhub.web.dto;

import java.time.Instant;
import java.util.List;

public record ImportBatchDto(
        Long id,
        String batchKey,
        String fileName,
        int rowsAccepted,
        int rowsRejected,
        String status,
        Instant startedAt,
        Instant finishedAt,
        List<String> duplicates,
        List<ImportErrorDto> errors
) {}
