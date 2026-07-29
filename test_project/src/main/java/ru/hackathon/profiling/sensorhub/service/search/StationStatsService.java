package ru.hackathon.profiling.sensorhub.service.search;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.MetricType;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.MetricTypeRepository;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.StationNotFoundException;
import ru.hackathon.profiling.sensorhub.web.dto.StationStatsDto;
import ru.hackathon.profiling.sensorhub.web.dto.StationStatsDto.StationStatsRowDto;
import ru.hackathon.profiling.sensorhub.web.dto.StationStatsDto.StationStatsTotalsDto;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.*;

@Service
public class StationStatsService {

    private final StationRepository stationRepository;
    private final RawSampleRepository rawSampleRepository;
    private final MetricTypeRepository metricTypeRepository;

    public StationStatsService(StationRepository stationRepository,
                               RawSampleRepository rawSampleRepository,
                               MetricTypeRepository metricTypeRepository) {
        this.stationRepository = stationRepository;
        this.rawSampleRepository = rawSampleRepository;
        this.metricTypeRepository = metricTypeRepository;
    }

    @Transactional(readOnly = true)
    public StationStatsDto getStats(String code, LocalDate from, LocalDate to) {
        if (from.isAfter(to)) {
            throw new ApiException("RANGE_INVALID", "from date must not be after to date", HttpStatus.BAD_REQUEST);
        }

        Station station = stationRepository.findByCodeIgnoreCase(code)
                .orElseThrow(() -> new StationNotFoundException(code));

        List<MetricType> metricTypes = metricTypeRepository.findAll();
        List<RawSample> samples = rawSampleRepository.searchSamples(
                station.getId(),
                null,
                from.atStartOfDay(ZoneOffset.UTC).toInstant(),
                to.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant(),
                null,
                org.springframework.data.domain.PageRequest.of(0, 10000)
        ).getContent();

        List<StationStatsRowDto> rows = new ArrayList<>();
        long totalSamples = 0;
        double sumMeasured = 0.0;

        for (MetricType mt : metricTypes) {
            long mSamples = 0;
            double mSum = 0.0;
            for (RawSample rs : samples) {
                if (mt.getCode().equals(rs.getMetricCode())) {
                    mSamples++;
                    mSum += rs.getMeasured();
                }
            }

            Double avgMeasured = mSamples > 0 ?
                    BigDecimal.valueOf(mSum / mSamples).setScale(3, RoundingMode.HALF_UP).doubleValue() : 0.000;

            rows.add(new StationStatsRowDto(mt.getCode(), from, mSamples, avgMeasured));
            totalSamples += mSamples;
            sumMeasured += mSum;
        }

        Double totalAvg = totalSamples > 0 ?
                BigDecimal.valueOf(sumMeasured / totalSamples).setScale(3, RoundingMode.HALF_UP).doubleValue() : 0.000;

        return new StationStatsDto(
                station.getCode(),
                from,
                to,
                rows,
                new StationStatsTotalsDto(totalSamples, totalAvg)
        );
    }
}
