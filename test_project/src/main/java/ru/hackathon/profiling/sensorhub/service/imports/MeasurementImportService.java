package ru.hackathon.profiling.sensorhub.service.imports;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.ImportBatch;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.ImportBatchRepository;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.dto.ImportBatchDto;
import ru.hackathon.profiling.sensorhub.web.dto.ImportErrorDto;

import java.time.Instant;
import java.util.*;

@Service
public class MeasurementImportService {

    private final ImportBatchRepository importBatchRepository;
    private final RawSampleRepository rawSampleRepository;
    private final StationRepository stationRepository;
    private final ImportSourceReader importSourceReader;

    public record ImportResult(ImportBatchDto dto, boolean isNew) {}

    public MeasurementImportService(ImportBatchRepository importBatchRepository,
                                    RawSampleRepository rawSampleRepository,
                                    StationRepository stationRepository,
                                    ImportSourceReader importSourceReader) {
        this.importBatchRepository = importBatchRepository;
        this.rawSampleRepository = rawSampleRepository;
        this.stationRepository = stationRepository;
        this.importSourceReader = importSourceReader;
    }

    @Transactional
    public ImportResult processImport(String batchKey, String source, String mode) {
        Optional<ImportBatch> existing = importBatchRepository.findByBatchKey(batchKey);
        if (existing.isPresent()) {
            ImportBatch b = existing.get();
            ImportBatchDto dto = new ImportBatchDto(
                    b.getId(), b.getBatchKey(), b.getFileName(),
                    b.getRowsAccepted(), b.getRowsRejected(), b.getStatus(),
                    b.getStartedAt(), b.getFinishedAt(), Collections.emptyList(), Collections.emptyList()
            );
            return new ImportResult(dto, false);
        }

        List<String> lines = importSourceReader.readLines(source);
        Instant startedAt = Instant.now();

        DuplicateDetector duplicateDetector = new DuplicateDetector();
        List<ImportErrorDto> errors = new ArrayList<>();
        List<RawSample> validSamples = new ArrayList<>();
        int accepted = 0;
        int rejected = 0;

        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i).trim();
            if (line.isEmpty()) continue;
            if (i == 0 && line.toLowerCase().startsWith("stationcode")) {
                continue; // skip header
            }
            int lineNumber = i + 1; // 1-based line number

            List<String> tokens = CsvRowParser.parseCsvLine(line);
            if (tokens.size() < 4) {
                errors.add(new ImportErrorDto(lineNumber, "FORMAT_ERROR", "Insufficient columns"));
                rejected++;
                continue;
            }

            String stCode = tokens.get(0);
            String metric = tokens.get(1);
            String rawVal = tokens.get(2);
            String rawTime = tokens.get(3);
            String quality = tokens.size() > 4 ? tokens.get(4) : "GOOD";

            Double val;
            try {
                val = ValueParser.parseDouble(rawVal);
            } catch (Exception e) {
                errors.add(new ImportErrorDto(lineNumber, "NUMBER_EXPECTED", "Invalid number: " + rawVal));
                rejected++;
                continue;
            }

            Instant takenAt;
            try {
                takenAt = ValueParser.parseInstant(rawTime);
            } catch (Exception e) {
                errors.add(new ImportErrorDto(lineNumber, "DATETIME_EXPECTED", "Invalid datetime: " + rawTime));
                rejected++;
                continue;
            }

            String dedupKey = stCode + "|" + metric + "|" + takenAt;
            duplicateDetector.process(dedupKey);

            Station station = stationRepository.findByCodeIgnoreCase(stCode).orElse(null);
            Long stId = station != null ? station.getId() : 9999L;

            RawSample rs = new RawSample();
            rs.setStationId(stId);
            rs.setMetricCode(metric);
            rs.setMeasured(val);
            rs.setTakenAt(takenAt);
            rs.setQuality(quality);
            validSamples.add(rs);
            accepted++;
        }

        String status = errors.isEmpty() ? "DONE" : "FAILED";
        if (status.equals("DONE") && !mode.equalsIgnoreCase("parse") && !mode.equalsIgnoreCase("dedup")) {
            rawSampleRepository.saveAll(validSamples);
        } else if (!errors.isEmpty()) {
            accepted = 0; // atomic failure
        }

        ImportBatch batch = new ImportBatch();
        batch.setBatchKey(batchKey);
        batch.setFileName(source);
        batch.setRowsAccepted(accepted);
        batch.setRowsRejected(rejected);
        batch.setStatus(status);
        batch.setStartedAt(startedAt);
        batch.setFinishedAt(Instant.now());

        ImportBatch saved = importBatchRepository.save(batch);

        ImportBatchDto dto = new ImportBatchDto(
                saved.getId(), saved.getBatchKey(), saved.getFileName(),
                saved.getRowsAccepted(), saved.getRowsRejected(), saved.getStatus(),
                saved.getStartedAt(), saved.getFinishedAt(),
                duplicateDetector.getDuplicates(), errors
        );
        return new ImportResult(dto, true);
    }

    @Transactional(readOnly = true)
    public ImportBatchDto getBatch(Long id) {
        ImportBatch b = importBatchRepository.findById(id)
                .orElseThrow(() -> new ApiException("IMPORT_BATCH_NOT_FOUND", "Import batch " + id + " not found", HttpStatus.NOT_FOUND));

        return new ImportBatchDto(
                b.getId(), b.getBatchKey(), b.getFileName(),
                b.getRowsAccepted(), b.getRowsRejected(), b.getStatus(),
                b.getStartedAt(), b.getFinishedAt(),
                Collections.emptyList(), Collections.emptyList()
        );
    }
}
