package ru.hackathon.profiling.sensorhub.service.report;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.repo.SampleOverviewRepository;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.dto.OverviewDto;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.List;

@Service
public class SampleOverviewService {

    private final SampleOverviewRepository overviewRepository;

    public SampleOverviewService(SampleOverviewRepository overviewRepository) {
        this.overviewRepository = overviewRepository;
    }

    @Transactional(readOnly = true)
    public OverviewDto getOverview(Instant from, Instant to) {
        if (from != null && to != null && from.isAfter(to)) {
            throw new ApiException("RANGE_INVALID", "from must not be after to", HttpStatus.BAD_REQUEST);
        }

        List<Object[]> stats = overviewRepository.getOverviewStats(from, to);
        if (stats == null || stats.isEmpty() || stats.get(0)[0] == null) {
            return new OverviewDto(0L, 0.000, 0.000);
        }

        Object[] row = stats.get(0);
        long count = ((Number) row[0]).longValue();
        if (count == 0) {
            return new OverviewDto(0L, 0.000, 0.000);
        }

        double avg = ((Number) row[1]).doubleValue();
        double max = ((Number) row[2]).doubleValue();

        Double avgRounded = BigDecimal.valueOf(avg).setScale(3, RoundingMode.HALF_UP).doubleValue();
        Double maxRounded = BigDecimal.valueOf(max).setScale(3, RoundingMode.HALF_UP).doubleValue();

        return new OverviewDto(count, avgRounded, maxRounded);
    }
}
