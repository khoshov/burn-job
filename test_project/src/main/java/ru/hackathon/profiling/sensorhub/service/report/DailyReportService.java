package ru.hackathon.profiling.sensorhub.service.report;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.dto.DailyRowDto;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.*;

@Service
public class DailyReportService {

    private final RawSampleRepository rawSampleRepository;
    private final StationRepository stationRepository;

    public DailyReportService(RawSampleRepository rawSampleRepository, StationRepository stationRepository) {
        this.rawSampleRepository = rawSampleRepository;
        this.stationRepository = stationRepository;
    }

    @Transactional(readOnly = true)
    public List<DailyRowDto> getDailyReport(LocalDate from, LocalDate to) {
        if (from.isAfter(to)) {
            throw new ApiException("RANGE_INVALID", "from date must not be after to date", HttpStatus.BAD_REQUEST);
        }

        List<RawSample> samples = rawSampleRepository.searchSamples(
                null,
                null,
                from.atStartOfDay(ZoneOffset.UTC).toInstant(),
                to.plusDays(1).atStartOfDay(ZoneOffset.UTC).toInstant(),
                null,
                org.springframework.data.domain.PageRequest.of(0, 100000)
        ).getContent();

        Map<Long, String> stationCodeMap = new HashMap<>();

        class AggKey {
            final LocalDate day;
            final Long stationId;
            AggKey(LocalDate day, Long stationId) {
                this.day = day;
                this.stationId = stationId;
            }
            @Override
            public boolean equals(Object o) {
                if (this == o) return true;
                if (o == null || getClass() != o.getClass()) return false;
                AggKey aggKey = (AggKey) o;
                return Objects.equals(day, aggKey.day) && Objects.equals(stationId, aggKey.stationId);
            }
            @Override
            public int hashCode() {
                return Objects.hash(day, stationId);
            }
        }

        class Stat {
            long count = 0;
            double sum = 0.0;
            double max = Double.NEGATIVE_INFINITY;
        }

        Map<AggKey, Stat> agg = new HashMap<>();

        for (RawSample rs : samples) {
            LocalDate day = rs.getTakenAt().atZone(ZoneOffset.UTC).toLocalDate();
            AggKey key = new AggKey(day, rs.getStationId());
            Stat st = agg.computeIfAbsent(key, k -> new Stat());
            st.count++;
            st.sum += rs.getMeasured();
            if (rs.getMeasured() > st.max) {
                st.max = rs.getMeasured();
            }
        }

        List<DailyRowDto> result = new ArrayList<>();
        for (Map.Entry<AggKey, Stat> entry : agg.entrySet()) {
            Long stId = entry.getKey().stationId;
            String code = stationCodeMap.computeIfAbsent(stId, id ->
                    stationRepository.findById(id).map(Station::getCode).orElse("ST-" + String.format("%06d", id)));

            Stat st = entry.getValue();
            Double avg = BigDecimal.valueOf(st.sum / st.count).setScale(3, RoundingMode.HALF_UP).doubleValue();
            Double max = BigDecimal.valueOf(st.max).setScale(3, RoundingMode.HALF_UP).doubleValue();

            result.add(new DailyRowDto(entry.getKey().day, code, st.count, avg, max));
        }

        result.sort(Comparator.comparing(DailyRowDto::day).thenComparing(DailyRowDto::stationCode));
        return result;
    }
}
