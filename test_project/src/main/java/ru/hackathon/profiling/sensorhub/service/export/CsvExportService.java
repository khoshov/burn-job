package ru.hackathon.profiling.sensorhub.service.export;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.config.AppProperties;
import ru.hackathon.profiling.sensorhub.domain.RawSample;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.RawSampleRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.support.Csv;

import java.io.Writer;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class CsvExportService {

    private final RawSampleRepository rawSampleRepository;
    private final StationRepository stationRepository;
    private final AppProperties appProperties;

    public CsvExportService(RawSampleRepository rawSampleRepository,
                            StationRepository stationRepository,
                            AppProperties appProperties) {
        this.rawSampleRepository = rawSampleRepository;
        this.stationRepository = stationRepository;
        this.appProperties = appProperties;
    }

    @Transactional(readOnly = true)
    public void exportSamples(Instant from, Instant to, String metric, Integer limitParam, Writer writer) throws Exception {
        int defaultLimit = appProperties.getLimits().getExportDefaultRows();
        int maxLimit = appProperties.getLimits().getExportMaxRows();

        int limit = (limitParam == null || limitParam <= 0) ? defaultLimit : Math.min(limitParam, maxLimit);

        List<RawSample> samples = rawSampleRepository.findForExport(from, to, metric, PageRequest.of(0, limit));
        Map<Long, String> stationCodeMap = new HashMap<>();

        writer.write("id,stationCode,metricCode,measured,takenAt,quality\n");

        for (RawSample rs : samples) {
            String code = stationCodeMap.computeIfAbsent(rs.getStationId(), id ->
                    stationRepository.findById(id).map(Station::getCode).orElse("ST-" + String.format("%06d", id)));

            String quality = rs.getQuality() != null ? rs.getQuality() : "GOOD";

            writer.write(String.format("%d,%s,%s,%s,%s,%s\n",
                    rs.getId(),
                    Csv.escape(code),
                    Csv.escape(rs.getMetricCode()),
                    Csv.formatDouble(rs.getMeasured()),
                    rs.getTakenAt().toString(),
                    Csv.escape(quality)
            ));
        }
        writer.flush();
    }
}
