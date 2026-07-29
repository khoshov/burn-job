package ru.hackathon.profiling.sensorhub.service.search;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.web.dto.SampleDto;
import ru.hackathon.profiling.sensorhub.web.mapper.SampleDtoMapper;

import java.time.Instant;

@Service
public class MeasurementSearchService {

    private final RawSampleRepository rawSampleRepository;
    private final StationRepository stationRepository;

    public MeasurementSearchService(RawSampleRepository rawSampleRepository, StationRepository stationRepository) {
        this.rawSampleRepository = rawSampleRepository;
        this.stationRepository = stationRepository;
    }

    @Transactional(readOnly = true)
    public Page<SampleDto> search(String stationCode, String metric, Instant from, Instant to, Double minMeasured, Pageable pageable) {
        int effectiveSize = Math.min(pageable.getPageSize(), 500);
        Pageable cappedPageable = PageRequest.of(pageable.getPageNumber(), effectiveSize,
                Sort.by(Sort.Order.desc("takenAt"), Sort.Order.asc("id")));

        Long stationId = null;
        if (stationCode != null && !stationCode.isBlank()) {
            stationId = stationRepository.findByCodeIgnoreCase(stationCode)
                    .map(Station::getId)
                    .orElse(-1L);
        }

        Page<RawSample> page = rawSampleRepository.searchSamples(stationId, metric, from, to, minMeasured, cappedPageable);

        return page.map(rs -> {
            String code = stationRepository.findById(rs.getStationId())
                    .map(Station::getCode)
                    .orElse("ST-" + String.format("%06d", rs.getStationId()));
            return SampleDtoMapper.toDto(rs, code);
        });
    }
}
