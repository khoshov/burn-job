package ru.hackathon.profiling.sensorhub.service.measurement;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.Measurement;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.MeasurementRepository;
import ru.hackathon.profiling.sensorhub.repo.MetricTypeRepository;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.MetricTypeNotFoundException;
import ru.hackathon.profiling.sensorhub.web.StationNotFoundException;
import ru.hackathon.profiling.sensorhub.web.dto.MeasurementCreateRequest;
import ru.hackathon.profiling.sensorhub.web.dto.MeasurementCreateResult;
import ru.hackathon.profiling.sensorhub.web.dto.MeasurementItemDto;

import java.util.ArrayList;
import java.util.List;

@Service
public class MeasurementCommandService {

    private final MeasurementRepository measurementRepository;
    private final RawSampleRepository rawSampleRepository;
    private final StationRepository stationRepository;
    private final MetricTypeRepository metricTypeRepository;

    public MeasurementCommandService(MeasurementRepository measurementRepository,
                                     RawSampleRepository rawSampleRepository,
                                     StationRepository stationRepository,
                                     MetricTypeRepository metricTypeRepository) {
        this.measurementRepository = measurementRepository;
        this.rawSampleRepository = rawSampleRepository;
        this.stationRepository = stationRepository;
        this.metricTypeRepository = metricTypeRepository;
    }

    @Transactional
    public MeasurementCreateResult createBatch(MeasurementCreateRequest request) {
        if (request.items() == null || request.items().size() > MeasurementCreateRequest.MAX_ITEMS) {
            throw new ApiException("TOO_MANY_ITEMS", "Batch size exceeds limit of 200 items", HttpStatus.BAD_REQUEST);
        }

        List<Measurement> measurementsToSave = new ArrayList<>();
        List<RawSample> rawSamplesToSave = new ArrayList<>();

        for (MeasurementItemDto item : request.items()) {
            Station station = stationRepository.findByCodeIgnoreCase(item.stationCode())
                    .orElseThrow(() -> new StationNotFoundException(item.stationCode()));

            if (!metricTypeRepository.existsById(item.metricCode())) {
                throw new MetricTypeNotFoundException(item.metricCode());
            }

            Measurement m = new Measurement();
            m.setStation(station);
            m.setMetricCode(item.metricCode());
            m.setMeasured(item.measured());
            m.setTakenAt(item.takenAt());
            m.setQualityFlag(item.qualityFlag());
            m.setNoteText("Batch import");
            measurementsToSave.add(m);

            RawSample rs = new RawSample();
            rs.setStationId(station.getId());
            rs.setMetricCode(item.metricCode());
            rs.setMeasured(item.measured());
            rs.setTakenAt(item.takenAt());
            rs.setQuality(item.qualityFlag() != null && item.qualityFlag() == 1 ? "GOOD" : "BAD");
            rawSamplesToSave.add(rs);
        }

        measurementRepository.saveAll(measurementsToSave);
        rawSampleRepository.saveAll(rawSamplesToSave);

        return new MeasurementCreateResult(measurementsToSave.size());
    }
}
