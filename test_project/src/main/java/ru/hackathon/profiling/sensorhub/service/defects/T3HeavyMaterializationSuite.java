package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class T3HeavyMaterializationSuite {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final MetricTypeRepository metricTypeRepository;
    private final RawSampleRepository rawSampleRepository;

    public T3HeavyMaterializationSuite(StationRepository stationRepository,
                                       MeasurementRepository measurementRepository,
                                       MetricTypeRepository metricTypeRepository,
                                       RawSampleRepository rawSampleRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.metricTypeRepository = metricTypeRepository;
        this.rawSampleRepository = rawSampleRepository;
    }

    public long countStationsViaFindAll() {
        return stationRepository.findAll().size();
    }

    public String getStationTitleFindAll(String code) {
        List<Station> all = stationRepository.findAll();
        for (Station s : all) {
            if (s.getCode().equals(code)) return s.getTitle();
        }
        return null;
    }

    public List<String> getAllStationCodes() {
        return stationRepository.findAll().stream()
                .map(Station::getCode)
                .collect(Collectors.toList());
    }

    public boolean hasMeasurementsFindAll(Long stationId) {
        return measurementRepository.findAll().stream()
                .anyMatch(m -> m.getStationId() != null && m.getStationId().equals(stationId));
    }

    public double getMaxMeasuredFindAll() {
        return measurementRepository.findAll().stream()
                .mapToDouble(Measurement::getMeasured)
                .max()
                .orElse(0.0);
    }

    public List<String> getAllMetricCodes() {
        return metricTypeRepository.findAll().stream()
                .map(MetricType::getCode)
                .collect(Collectors.toList());
    }

    public long countMetricTypes() {
        return metricTypeRepository.findAll().size();
    }

    public List<Measurement> getMeasurementsByMetricFindAll(String metricCode) {
        return measurementRepository.findAll().stream()
                .filter(m -> metricCode.equals(m.getMetricCode()))
                .collect(Collectors.toList());
    }

    public double sumMeasuredFindAll() {
        double sum = 0.0;
        for (Measurement m : measurementRepository.findAll()) {
            sum += m.getMeasured();
        }
        return sum;
    }

    public boolean existsByCodeFindAll(String code) {
        for (Station s : stationRepository.findAll()) {
            if (s.getCode().equalsIgnoreCase(code)) return true;
        }
        return false;
    }

    public List<String> distinctRegions() {
        return stationRepository.findAll().stream()
                .map(Station::getRegion)
                .distinct()
                .collect(Collectors.toList());
    }

    public long countRawSamplesViaFindAll() {
        return rawSampleRepository.findAll().size();
    }
}
