package ru.hackathon.profiling.sensorhub.service.report;

import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.SampleOverviewRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.dto.TopRowDto;

import java.util.Collections;
import java.util.List;

@Service
public class TopReportService {

    private final SampleOverviewRepository overviewRepository;
    private final StationRepository stationRepository;

    public TopReportService(SampleOverviewRepository overviewRepository, StationRepository stationRepository) {
        this.overviewRepository = overviewRepository;
        this.stationRepository = stationRepository;
    }

    @Transactional(readOnly = true)
    public List<TopRowDto> getTop(String metric, int limit) {
        if (limit < 0 || limit > 100) {
            throw new ApiException("LIMIT_INVALID", "limit must be between 0 and 100", HttpStatus.BAD_REQUEST);
        }
        if (limit == 0) {
            return Collections.emptyList();
        }

        List<RawSample> samples = overviewRepository.findTopByMetric(metric, PageRequest.of(0, limit));

        return samples.stream().map(rs -> {
            String code = stationRepository.findById(rs.getStationId())
                    .map(Station::getCode)
                    .orElse("ST-" + String.format("%06d", rs.getStationId()));
            return new TopRowDto(code, rs.getMetricCode(), rs.getMeasured(), rs.getTakenAt());
        }).toList();
    }
}
