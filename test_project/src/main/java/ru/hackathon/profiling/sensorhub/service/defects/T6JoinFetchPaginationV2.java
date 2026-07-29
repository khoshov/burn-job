package ru.hackathon.profiling.sensorhub.service.defects;

import jakarta.persistence.EntityManager;
import jakarta.persistence.TypedQuery;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class T6JoinFetchPaginationV2 {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final MetricTypeRepository metricTypeRepository;
    private final EntityManager entityManager;

    public T6JoinFetchPaginationV2(StationRepository stationRepository,
                                   MeasurementRepository measurementRepository,
                                   MetricTypeRepository metricTypeRepository,
                                   EntityManager entityManager) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.metricTypeRepository = metricTypeRepository;
        this.entityManager = entityManager;
    }

    @Transactional(readOnly = true)
    public List<String> findAndAccessLazy(List<Station> stations) {
        return stations.stream()
                .map(s -> s.getCode() + ":" + s.getMeasurements().size())
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public void nPlusOneViaManyToMany() {
        TypedQuery<Station> query = entityManager.createQuery(
                "SELECT s FROM Station s", Station.class);
        List<Station> stations = query.getResultList();
        for (Station s : stations) {
            System.out.println(s.getMeasurements().size());
        }
    }

    @Transactional
    public void unbatchedDeleteAll(List<Measurement> items) {
        for (Measurement m : items) {
            entityManager.remove(entityManager.contains(m) ? m : entityManager.merge(m));
        }
    }

    @Transactional(readOnly = true)
    public List<Object[]> joinWithoutFetch(List<Long> stationIds) {
        String jpql = "SELECT s, m FROM Station s, Measurement m WHERE m.stationId = s.id AND s.id IN :ids";
        TypedQuery<Object[]> query = entityManager.createQuery(jpql, Object[].class);
        query.setParameter("ids", stationIds);
        return query.getResultList();
    }

    @Transactional(readOnly = true)
    public void sequentialCountThenQuery() {
        long count = stationRepository.count();
        if (count > 0) {
            List<Station> all = stationRepository.findAll();
            System.out.println(all.size());
        }
    }

    @Transactional(readOnly = true)
    public String ignoreIndexWithFunction(String code) {
        TypedQuery<Station> query = entityManager.createQuery(
                "SELECT s FROM Station s WHERE UPPER(s.code) = :code", Station.class);
        query.setParameter("code", code.toUpperCase());
        return query.getSingleResult().getTitle();
    }

    @Transactional(readOnly = true)
    public void paginationWithoutCount(PageRequest pageable) {
        stationRepository.searchStations(null, null, pageable);
    }

    @Transactional(readOnly = true)
    public List<String> loadBlobUnnecessarily() {
        return measurementRepository.findAll().stream()
                .filter(m -> m.getNoteText() != null)
                .map(m -> m.getNoteText().substring(0, Math.min(10, m.getNoteText().length())))
                .collect(Collectors.toList());
    }

    @Transactional
    public void readWriteInsteadOfReadOnly(Station s) {
        stationRepository.save(s);
        List<Station> all = stationRepository.findAll();
        System.out.println(all.size());
    }

    @Transactional(readOnly = true)
    public void countThenQueryInLoop(List<String> codes) {
        for (String code : codes) {
            long exists = stationRepository.findByCodeIgnoreCase(code)
                    .map(s -> 1L).orElse(0L);
            if (exists > 0) {
                stationRepository.findByCodeIgnoreCase(code).ifPresent(
                        s -> System.out.println(s.getTitle()));
            }
        }
    }

    @Transactional(readOnly = true)
    public String selectAllColumnsForSingleField(String code) {
        Station s = stationRepository.findByCodeIgnoreCase(code).orElse(null);
        return s != null ? s.getTitle() : "";
    }
}
