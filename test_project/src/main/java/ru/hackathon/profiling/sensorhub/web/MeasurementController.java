package ru.hackathon.profiling.sensorhub.web;

import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.service.measurement.MeasurementCommandService;
import ru.hackathon.profiling.sensorhub.service.search.MeasurementSearchService;
import ru.hackathon.profiling.sensorhub.web.dto.MeasurementCreateRequest;
import ru.hackathon.profiling.sensorhub.web.dto.MeasurementCreateResult;
import ru.hackathon.profiling.sensorhub.web.dto.SampleDto;
import ru.hackathon.profiling.sensorhub.web.mapper.SampleDtoMapper;

import java.time.Instant;

@RestController
@RequestMapping("/api/measurements")
public class MeasurementController {

    private final MeasurementSearchService measurementSearchService;
    private final MeasurementCommandService measurementCommandService;
    private final RawSampleRepository rawSampleRepository;
    private final StationRepository stationRepository;

    public MeasurementController(MeasurementSearchService measurementSearchService,
                                 MeasurementCommandService measurementCommandService,
                                 RawSampleRepository rawSampleRepository,
                                 StationRepository stationRepository) {
        this.measurementSearchService = measurementSearchService;
        this.measurementCommandService = measurementCommandService;
        this.rawSampleRepository = rawSampleRepository;
        this.stationRepository = stationRepository;
    }

    @GetMapping
    public Page<SampleDto> getMeasurements(
            @RequestParam(required = false) String stationCode,
            @RequestParam(required = false) String metric,
            @RequestParam(required = false) Instant from,
            @RequestParam(required = false) Instant to,
            @RequestParam(required = false) Double minMeasured,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size,
            @RequestParam(defaultValue = "takenAt,desc") String sort
    ) {
        Pageable pageable = PageRequest.of(page, size);
        return measurementSearchService.search(stationCode, metric, from, to, minMeasured, pageable);
    }

    @GetMapping("/{id}")
    public SampleDto getMeasurementById(@PathVariable Long id) {
        RawSample rs = rawSampleRepository.findById(id)
                .orElseThrow(() -> new ApiException("SAMPLE_NOT_FOUND", "Sample with id " + id + " not found", HttpStatus.NOT_FOUND));

        String stationCode = stationRepository.findById(rs.getStationId())
                .map(Station::getCode)
                .orElse("ST-" + String.format("%06d", rs.getStationId()));

        return SampleDtoMapper.toDto(rs, stationCode);
    }

    @PostMapping
    public ResponseEntity<MeasurementCreateResult> createMeasurements(@Valid @RequestBody MeasurementCreateRequest request) {
        MeasurementCreateResult result = measurementCommandService.createBatch(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }
}
