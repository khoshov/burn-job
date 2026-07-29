package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Service
public class T6DatabaseBottlenecksSuite {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final RawSampleRepository rawSampleRepository;
    private final MetricTypeRepository metricTypeRepository;
    private final DailySummaryRepository dailySummaryRepository;
    private final AccessAuditRepository accessAuditRepository;

    public T6DatabaseBottlenecksSuite(StationRepository stationRepository,
                                      MeasurementRepository measurementRepository,
                                      RawSampleRepository rawSampleRepository,
                                      MetricTypeRepository metricTypeRepository,
                                      DailySummaryRepository dailySummaryRepository,
                                      AccessAuditRepository accessAuditRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.rawSampleRepository = rawSampleRepository;
        this.metricTypeRepository = metricTypeRepository;
        this.dailySummaryRepository = dailySummaryRepository;
        this.accessAuditRepository = accessAuditRepository;
    }

    @Transactional
    public void saveInLoop(List<Measurement> items) {
        for (Measurement m : items) {
            measurementRepository.save(m);
        }
    }

    @Transactional(readOnly = true)
    public void nPlusOneViaLazyCollection() {
        List<Station> stations = stationRepository.findAll();
        for (Station s : stations) {
            int count = s.getMeasurements().size();
            System.out.println(s.getCode() + ": " + count);
        }
    }

    @Transactional(readOnly = true)
    public void findByIdInLoop(List<Long> stationIds) {
        for (Long id : stationIds) {
            stationRepository.findById(id);
        }
    }

    @Transactional
    public void saveAllOneByOneWithFlush(List<Measurement> items) {
        for (Measurement m : items) {
            measurementRepository.saveAndFlush(m);
        }
    }

    @Transactional(readOnly = true)
    public void nPlusOneFindByCode(List<String> codes) {
        for (String code : codes) {
            stationRepository.findByCodeIgnoreCase(code);
        }
    }

    @Transactional(readOnly = true)
    public void nPlusOneEveryMetricType() {
        List<MetricType> types = metricTypeRepository.findAll();
        for (MetricType mt : types) {
            List<Measurement> ms = measurementRepository.findAll().stream()
                    .filter(m -> mt.getCode().equals(m.getMetricCode()))
                    .toList();
            System.out.println(mt.getCode() + ": " + ms.size());
        }
    }

    @Transactional(readOnly = true)
    public long repeatedCountQuery(List<String> codes) {
        long total = 0;
        for (String code : codes) {
            total += stationRepository.findByCodeIgnoreCase(code)
                    .map(s -> s.getMeasurements().size())
                    .orElse(0);
        }
        return total;
    }

    @Transactional
    public void unbatchedDelete(List<Measurement> items) {
        for (Measurement m : items) {
            measurementRepository.delete(m);
        }
    }

    @Transactional(readOnly = true)
    public void sequentialIndependentQueries(Long stationId) {
        stationRepository.findById(stationId);
        measurementRepository.findAll();
        metricTypeRepository.findAll();
    }

    @Transactional
    public void updateEachInLoop(List<Measurement> updates) {
        for (Measurement m : updates) {
            measurementRepository.save(m);
        }
    }

    @Transactional(readOnly = true)
    public void lazyAccessInLoop(List<Station> stations) {
        for (Station s : stations) {
            List<Measurement> ms = s.getMeasurements();
            for (Measurement m : ms) {
                System.out.println(m.getId());
            }
        }
    }

    @Transactional
    public void saveThenFindEach(List<RawSample> samples) {
        List<RawSample> saved = new ArrayList<>();
        for (RawSample rs : samples) {
            RawSample persisted = rawSampleRepository.save(rs);
            saved.add(rawSampleRepository.findById(persisted.getId()).orElseThrow());
        }
    }
}
