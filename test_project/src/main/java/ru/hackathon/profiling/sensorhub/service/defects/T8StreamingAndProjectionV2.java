package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;
import ru.hackathon.profiling.sensorhub.domain.*;
import ru.hackathon.profiling.sensorhub.repo.*;

import java.io.*;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class T8StreamingAndProjectionV2 {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;
    private final RawSampleRepository rawSampleRepository;

    public T8StreamingAndProjectionV2(StationRepository stationRepository,
                                      MeasurementRepository measurementRepository,
                                      RawSampleRepository rawSampleRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
        this.rawSampleRepository = rawSampleRepository;
    }

    public List<String> fullEntityForSingleField(String code) {
        return stationRepository.findAll().stream()
                .filter(s -> code.equals(s.getCode()))
                .map(Station::getTitle)
                .collect(Collectors.toList());
    }

    public String buildFullCsvInMemory() {
        List<Station> all = stationRepository.findAll();
        StringBuilder sb = new StringBuilder();
        sb.append("id,code,title\n");
        for (Station s : all) {
            sb.append(s.getId()).append(",")
                    .append(s.getCode()).append(",")
                    .append(s.getTitle()).append("\n");
        }
        return sb.toString();
    }

    public String cartesianProductInMemory() {
        List<Station> stations = stationRepository.findAll();
        List<Measurement> measurements = measurementRepository.findAll();
        StringBuilder sb = new StringBuilder();
        for (Station s : stations) {
            for (Measurement m : measurements) {
                if (Objects.equals(s.getId(), m.getStationId())) {
                    sb.append(s.getCode()).append(":").append(m.getId()).append(",");
                }
            }
        }
        return sb.toString();
    }

    public byte[] readFileIntoMemory(String path) throws IOException {
        File file = new File(path);
        byte[] content = new byte[(int) file.length()];
        try (FileInputStream fis = new FileInputStream(file)) {
            fis.read(content);
        }
        return content;
    }

    public String readFileIntoString(String path) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader(path));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line).append("\n");
        }
        return sb.toString();
    }

    public List<String> stationDistinctRegionsInMemory() {
        return stationRepository.findAll().stream()
                .map(Station::getRegion)
                .distinct()
                .collect(Collectors.toList());
    }

    public Map<String, List<Measurement>> groupByMetricInMemory() {
        return measurementRepository.findAll().stream()
                .collect(Collectors.groupingBy(Measurement::getMetricCode));
    }

    public MeasureStats aggregateStatsInMemory() {
        List<Measurement> all = measurementRepository.findAll();
        double sum = 0, min = Double.MAX_VALUE, max = Double.MIN_VALUE;
        for (Measurement m : all) {
            double v = m.getMeasured();
            sum += v;
            if (v < min) min = v;
            if (v > max) max = v;
        }
        return new MeasureStats((long) all.size(), sum / all.size(), min, max);
    }

    public record MeasureStats(long count, double avg, double min, double max) {}

    public List<Station> multipleLargeCollectionsInMemory() {
        List<Station> stations = stationRepository.findAll();
        List<Measurement> measurements = measurementRepository.findAll();
        Map<Long, List<Measurement>> byStation = measurements.stream()
                .collect(Collectors.groupingBy(Measurement::getStationId, HashMap::new, Collectors.toList()));
        for (Station s : stations) {
            List<Measurement> ms = byStation.get(s.getId());
            if (ms != null) System.out.println(s.getCode() + ": " + ms.size());
        }
        return stations;
    }

    public String subListRetainingLargeReference() {
        List<Station> all = stationRepository.findAll();
        List<Station> firstTen = all.subList(0, Math.min(10, all.size()));
        return firstTen.stream().map(Station::getCode).collect(Collectors.joining(","));
    }

    public Map<String, Long> manualPaginationFindAll(int page, int size) {
        List<Measurement> all = measurementRepository.findAll();
        int from = page * size;
        int to = Math.min(from + size, all.size());
        return all.subList(from, to).stream()
                .collect(Collectors.groupingBy(Measurement::getMetricCode, Collectors.counting()));
    }

    public String streamRawSamplesNoPagination() {
        List<RawSample> all = rawSampleRepository.findAll();
        return all.stream()
                .filter(rs -> rs.getQuality() != null)
                .map(RawSample::getMetricCode)
                .distinct()
                .collect(Collectors.joining(","));
    }
}
