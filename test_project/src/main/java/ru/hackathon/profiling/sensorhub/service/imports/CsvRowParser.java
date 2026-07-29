package ru.hackathon.profiling.sensorhub.service.imports;

import ru.hackathon.profiling.sensorhub.web.dto.ImportErrorDto;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

public class CsvRowParser {

    public record ParsedRow(
            int lineNumber,
            String stationCode,
            String metricCode,
            Double measured,
            Instant takenAt,
            String quality
    ) {}

    public static List<String> parseCsvLine(String line) {
        List<String> result = new ArrayList<>();
        boolean inQuotes = false;
        StringBuilder sb = new StringBuilder();

        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == '"') {
                inQuotes = !inQuotes;
            } else if (c == ',' && !inQuotes) {
                result.add(sb.toString().trim());
                sb.setLength(0);
            } else {
                sb.append(c);
            }
        }
        result.add(sb.toString().trim());
        return result;
    }
}
