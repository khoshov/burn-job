package ru.hackathon.profiling.sensorhub.web;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.hackathon.profiling.sensorhub.service.imports.MeasurementImportService;
import ru.hackathon.profiling.sensorhub.service.imports.MeasurementImportService.ImportResult;
import ru.hackathon.profiling.sensorhub.web.dto.ImportBatchDto;

@RestController
@RequestMapping("/api/imports")
public class ImportController {

    private final MeasurementImportService measurementImportService;

    public ImportController(MeasurementImportService measurementImportService) {
        this.measurementImportService = measurementImportService;
    }

    @PostMapping
    public ResponseEntity<ImportBatchDto> createImport(
            @RequestParam String batchKey,
            @RequestParam String source,
            @RequestParam(defaultValue = "all") String mode
    ) {
        if (batchKey == null || batchKey.isBlank() || batchKey.length() > 128) {
            throw new ApiException("VALIDATION_FAILED", "batchKey must be non-empty and <= 128 chars", HttpStatus.BAD_REQUEST);
        }
        if (source == null || source.isBlank() || source.length() > 256) {
            throw new ApiException("VALIDATION_FAILED", "source must be non-empty and <= 256 chars", HttpStatus.BAD_REQUEST);
        }

        ImportResult result = measurementImportService.processImport(batchKey, source, mode);
        HttpStatus status = result.isNew() ? HttpStatus.ACCEPTED : HttpStatus.OK;
        return ResponseEntity.status(status).body(result.dto());
    }

    @GetMapping("/{id}")
    public ImportBatchDto getImportById(@PathVariable Long id) {
        return measurementImportService.getBatch(id);
    }
}
