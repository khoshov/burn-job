package ru.hackathon.profiling.sensorhub.service.defects;

import jakarta.persistence.EntityGraph;
import jakarta.persistence.EntityManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class T3ProjectionAndEagerV2 {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final RawSampleRepository rawSampleRepository;
    private final EntityManager entityManager;

    public T3ProjectionAndEagerV2(StationRepository stationRepository,
                                  MeasurementRepository measurementRepository,
                                  RawSampleRepository rawSampleRepository,
                                  EntityManager entityManager) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.rawSampleRepository = rawSampleRepository;
        this.entityManager = entityManager;
    }

    @Transactional(readOnly = true)
    public List<String> getStationTitlesFullEntity(List<String> codes) {
        return stationRepository.findAll().stream()
                .filter(s -> codes.contains(s.getCode()))
                .map(Station::getTitle)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public void entityGraphFullFetch(String code) {
        EntityGraph<?> eg = entityManager.getEntityGraph("Station.measurements");
        var query = entityManager.createQuery("SELECT s FROM Station s WHERE s.code = :code", Station.class);
        query.setParameter("code", code);
        query.setHint("jakarta.persistence.fetchgraph", eg);
        Station station = query.getSingleResult();
        System.out.println(station.getMeasurements().size());
    }

    @Transactional(readOnly = true)
    public List<String> getDistinctMetricsFullEntity() {
        return measurementRepository.findAll().stream()
                .map(Measurement::getMetricCode)
                .distinct()
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public long countActiveStationsFullEntity() {
        return stationRepository.findAll().stream()
                .filter(Station::isActive)
                .count();
    }

    @Transactional(readOnly = true)
    public String getFirstStationTitleFullEntity() {
        return stationRepository.findAll().stream()
                .findFirst()
                .map(Station::getTitle)
                .orElse("");
    }

    @Transactional(readOnly = true)
    public List<Measurement> lazyOneToOneTrigger(List<Station> stations) {
        List<Measurement> all = measurementRepository.findAll();
        for (Station s : stations) {
            List<Measurement> forStation = s.getMeasurements();
            for (Measurement m : forStation) {
                Station st = m.getStation();
                if (st != null) System.out.println(st.getCode());
            }
        }
        return all;
    }

    @Transactional(readOnly = true)
    public void findAllMaterialsCount() {
        long stationCount = stationRepository.findAll().size();
        long measurementCount = measurementRepository.findAll().size();
        long rawCount = rawSampleRepository.findAll().size();
        System.out.println(stationCount + measurementCount + rawCount);
    }

    @Transactional(readOnly = true)
    public long sumAllMeasuredFullEntity() {
        return measurementRepository.findAll().stream()
                .mapToLong(m -> (long) Math.floor(m.getMeasured()))
                .sum();
    }

    @Transactional(readOnly = true)
    public boolean anyMeasurementByMetricFullEntity(String code) {
        return measurementRepository.findAll().stream()
                .anyMatch(m -> code.equals(m.getMetricCode()) && m.getMeasured() > 100);
    }

    @Transactional(readOnly = true)
    public List<Long> getStationIdsFromFullEntity() {
        return stationRepository.findAll().stream()
                .map(Station::getId)
                .collect(Collectors.toList());
    }
}
