package ru.hackathon.profiling.sensorhub.service.defects.correct;

import jakarta.persistence.EntityManager;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class T6CorrectPatterns {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final MetricTypeRepository metricTypeRepository;
    private final RawSampleRepository rawSampleRepository;
    private final EntityManager entityManager;

    public T6CorrectPatterns(StationRepository stationRepository,
                             MeasurementRepository measurementRepository,
                             MetricTypeRepository metricTypeRepository,
                             RawSampleRepository rawSampleRepository,
                             EntityManager entityManager) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.metricTypeRepository = metricTypeRepository;
        this.rawSampleRepository = rawSampleRepository;
        this.entityManager = entityManager;
    }

    @Transactional
    public void batchSave(List<Measurement> items) {
        measurementRepository.saveAll(items);
    }

    @Transactional(readOnly = true)
    public List<String> joinFetchStationsWithMeasurements() {
        var query = entityManager.createQuery(
                "SELECT DISTINCT s FROM Station s LEFT JOIN FETCH s.measurements", Station.class);
        List<Station> stations = query.getResultList();
        return stations.stream()
                .map(s -> s.getCode() + ":" + s.getMeasurements().size())
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public void batchFindByIds(List<Long> stationIds) {
        stationRepository.findAllById(stationIds);
    }

    @Transactional
    public void batchSaveAll(List<Measurement> items) {
        measurementRepository.saveAll(items);
    }

    @Transactional(readOnly = true)
    public void batchFindByCode(List<String> codes) {
        for (String code : codes) {
            stationRepository.findByCodeIgnoreCase(code);
        }
    }

    @Transactional(readOnly = true)
    public long countByCode(List<String> codes) {
        return codes.stream()
                .map(code -> stationRepository.findByCodeIgnoreCase(code))
                .filter(Optional::isPresent)
                .count();
    }

    @Transactional
    public void batchDelete(List<Measurement> items) {
        measurementRepository.deleteAll(items);
    }

    @Transactional(readOnly = true)
    public Page<Station> paginatedSearch(String query, String region, Pageable pageable) {
        return stationRepository.searchStations(query, region, pageable);
    }

    @Transactional
    public void singleTransaction(List<Measurement> items) {
        measurementRepository.saveAll(items);
        stationRepository.findAll();
    }

    @Transactional(readOnly = true)
    public long countStations() {
        return stationRepository.count();
    }

    @Transactional(readOnly = true)
    public List<String> findTitlesByCodes(List<String> codes) {
        return stationRepository.findAll().stream()
                .filter(s -> codes.contains(s.getCode()))
                .map(Station::getTitle)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public String findTitleByCode(String code) {
        return stationRepository.findByCodeIgnoreCase(code)
                .map(Station::getTitle)
                .orElse("");
    }

    @Transactional
    public void saveOnce(List<RawSample> samples) {
        rawSampleRepository.saveAll(samples);
    }
}
