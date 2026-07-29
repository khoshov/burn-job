package ru.hackathon.profiling.sensorhub.service.imports;

import java.time.Instant;

public class ValueParser {

    public static Double parseDouble(String str) {
        if (str == null || str.isBlank()) {
            throw new IllegalArgumentException("NUMBER_EXPECTED");
        }
        try {
            return Double.parseDouble(str.trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("NUMBER_EXPECTED");
        }
    }

    public static Instant parseInstant(String str) {
        if (str == null || str.isBlank()) {
            throw new IllegalArgumentException("DATETIME_EXPECTED");
        }
        try {
            return Instant.parse(str.trim());
        } catch (Exception e) {
            throw new IllegalArgumentException("DATETIME_EXPECTED");
        }
    }
}
