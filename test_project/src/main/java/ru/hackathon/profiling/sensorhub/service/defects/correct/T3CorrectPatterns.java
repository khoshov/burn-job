package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.List;
import java.util.Optional;

@Service
public class T3CorrectPatterns {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final MetricTypeRepository metricTypeRepository;
    private final RawSampleRepository rawSampleRepository;

    public T3CorrectPatterns(StationRepository stationRepository,
                             MeasurementRepository measurementRepository,
                             MetricTypeRepository metricTypeRepository,
                             RawSampleRepository rawSampleRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.metricTypeRepository = metricTypeRepository;
        this.rawSampleRepository = rawSampleRepository;
    }

    @Transactional(readOnly = true)
    public boolean existsByCode(String code) {
        return stationRepository.existsByCode(code);
    }

    @Transactional(readOnly = true)
    public long stationCount() {
        return stationRepository.count();
    }

    @Transactional(readOnly = true)
    public Optional<String> findStationTitleByCode(String code) {
        return stationRepository.findByCodeIgnoreCase(code).map(Station::getTitle);
    }

    @Transactional(readOnly = true)
    public Optional<Station> findByCode(String code) {
        return stationRepository.findByCodeIgnoreCase(code);
    }

    @Transactional(readOnly = true)
    public Page<Station> searchStations(String query, String region, Pageable pageable) {
        return stationRepository.searchStations(query, region, pageable);
    }

    @Transactional(readOnly = true)
    public List<String> findStationCodesByRegion(String region) {
        return stationRepository.searchStations(null, region, Pageable.unpaged())
                .stream().map(Station::getCode).toList();
    }

    @Transactional(readOnly = true)
    public boolean hasMeasurements(Long stationId) {
        return measurementRepository.findById(stationId).isPresent();
    }

    @Transactional(readOnly = true)
    public long countMetricTypes() {
        return metricTypeRepository.count();
    }

    @Transactional(readOnly = true)
    public Page<RawSample> searchSamples(Long stationId, String metric, Pageable pageable) {
        return rawSampleRepository.searchSamples(stationId, metric, null, null, null, pageable);
    }

    @Transactional(readOnly = true)
    public List<String> findDistinctRegions() {
        return stationRepository.searchStations(null, null, Pageable.unpaged())
                .stream().map(Station::getRegion).distinct().toList();
    }

    @Transactional(readOnly = true)
    public Optional<Measurement> findMeasurementById(Long id) {
        return measurementRepository.findById(id);
    }
}
