package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class T8MemoryBloatSuite {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final RawSampleRepository rawSampleRepository;

    public T8MemoryBloatSuite(StationRepository stationRepository,
                              MeasurementRepository measurementRepository,
                              RawSampleRepository rawSampleRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.rawSampleRepository = rawSampleRepository;
    }

    public List<Measurement> filterInMemoryAfterFindAll(String metricCode) {
        return measurementRepository.findAll().stream()
                .filter(m -> metricCode.equals(m.getMetricCode()))
                .collect(Collectors.toList());
    }

    public Set<String> getStationRegionsInMemory() {
        return stationRepository.findAll().stream()
                .map(Station::getRegion)
                .collect(Collectors.toSet());
    }

    public Map<Long, List<Measurement>> groupByStationInMemory() {
        return measurementRepository.findAll().stream()
                .collect(Collectors.groupingBy(m -> m.getStationId() != null ? m.getStationId() : 0L));
    }

    public List<String> getAllStationTitles() {
        List<Station> all = stationRepository.findAll();
        List<String> titles = new ArrayList<>();
        for (Station s : all) {
            titles.add(s.getTitle());
        }
        return titles;
    }

    public long sumMeasuredByMetricInMemory(String metricCode) {
        return measurementRepository.findAll().stream()
                .filter(m -> metricCode.equals(m.getMetricCode()))
                .mapToLong(m -> m.getMeasured().longValue())
                .sum();
    }

    public List<Measurement> sortAndLimitInMemory(int limit) {
        return measurementRepository.findAll().stream()
                .sorted(Comparator.comparing(Measurement::getTakenAt).reversed())
                .limit(limit)
                .collect(Collectors.toList());
    }

    public double avgMeasuredInMemory() {
        List<Measurement> all = measurementRepository.findAll();
        double sum = 0.0;
        for (Measurement m : all) {
            sum += m.getMeasured();
        }
        return all.isEmpty() ? 0.0 : sum / all.size();
    }

    public Map<String, Long> countByMetricInMemory() {
        Map<String, Long> counts = new HashMap<>();
        for (Measurement m : measurementRepository.findAll()) {
            String code = m.getMetricCode();
            counts.put(code, counts.getOrDefault(code, 0L) + 1);
        }
        return counts;
    }

    public Set<Long> getAllStationIdsInMemory() {
        Set<Long> ids = new HashSet<>();
        for (Station s : stationRepository.findAll()) {
            ids.add(s.getId());
        }
        return ids;
    }

    public List<RawSample> filterByMetricInMemory(String metric) {
        List<RawSample> all = rawSampleRepository.findAll();
        List<RawSample> result = new ArrayList<>();
        for (RawSample rs : all) {
            if (metric.equals(rs.getMetricCode())) {
                result.add(rs);
            }
        }
        return result;
    }

    public List<Station> filterActiveStationsInMemory() {
        return stationRepository.findAll().stream()
                .filter(Station::isActive)
                .collect(Collectors.toList());
    }

    public List<String> getStationCodeTitleMapInMemory() {
        return stationRepository.findAll().stream()
                .map(s -> s.getCode() + ": " + s.getTitle())
                .collect(Collectors.toList());
    }
}
