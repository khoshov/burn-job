package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class T8CorrectPatterns {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final RawSampleRepository rawSampleRepository;

    public T8CorrectPatterns(StationRepository stationRepository,
                             MeasurementRepository measurementRepository,
                             RawSampleRepository rawSampleRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.rawSampleRepository = rawSampleRepository;
    }

    @Transactional(readOnly = true)
    public List<Station> findByRegion(String region) {
        return stationRepository.searchStations(null, region, Pageable.unpaged()).getContent();
    }

    @Transactional(readOnly = true)
    public Set<String> findRegionsWithQuery() {
        return stationRepository.findAll().stream()
                .map(Station::getRegion)
                .collect(Collectors.toCollection(HashSet::new));
    }

    @Transactional(readOnly = true)
    public Map<Long, List<Measurement>> groupByStationWithDb(Long stationId) {
        List<Measurement> ms = measurementRepository.findAll();
        return ms.stream().collect(Collectors.groupingBy(m -> m.getStationId() != null ? m.getStationId() : 0L));
    }

    @Transactional(readOnly = true)
    public List<String> getActiveStationCodes() {
        return stationRepository.findAll().stream()
                .filter(Station::isActive)
                .map(Station::getCode)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public long countByMetricDb(String metricCode) {
        return measurementRepository.findAll().stream()
                .filter(m -> metricCode.equals(m.getMetricCode()))
                .count();
    }

    @Transactional(readOnly = true)
    public List<Measurement> getRecentMeasurements(int limit) {
        return measurementRepository.findAll().stream()
                .sorted(Comparator.comparing(Measurement::getTakenAt).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public Double avgMeasuredForStation(Long stationId) {
        List<Measurement> all = measurementRepository.findAll();
        return all.stream()
                .filter(m -> m.getStationId() != null && m.getStationId().equals(stationId))
                .mapToDouble(Measurement::getMeasured)
                .average()
                .orElse(0.0);
    }

    @Transactional(readOnly = true)
    public List<String> paginatedStationCodes(int page, int size) {
        Page<Station> stationPage = stationRepository.searchStations(
                null, null, PageRequest.of(page, size));
        return stationPage.getContent().stream()
                .map(Station::getCode)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<Station> getActiveStationsBatched() {
        return stationRepository.findAll().stream()
                .filter(Station::isActive)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public String getStationTitleById(Long id) {
        return stationRepository.findById(id)
                .map(Station::getTitle)
                .orElse("");
    }

    @Transactional(readOnly = true)
    public List<String> searchStationCodesPaginated(String query, int page, int size) {
        return stationRepository.searchStations(query, null, PageRequest.of(page, size))
                .stream().map(Station::getCode).collect(Collectors.toList());
    }
}
