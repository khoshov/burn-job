package ru.hackathon.profiling.sensorhub.seed;

import java.time.Instant;
import java.time.LocalDate;

public class SeedFormulas {

    public static final long SEED = 20260726L;
    public static final Instant BASE = Instant.parse("2026-04-01T00:00:00Z");

    public static final String[] METRICS = {
            "TEMP", "HUMID", "PRESS", "WIND", "RAIN", "DUST",
            "CO2", "NOISE", "LUX", "VOLT", "AMP", "FLOW"
    };

    public static long mix(long index, long salt) {
        long x = index ^ salt ^ SEED;
        x ^= (x << 13);
        x ^= (x >>> 7);
        x ^= (x << 17);
        return Math.abs(x);
    }

    public static String stationCode(int index) {
        return String.format("ST-%06d", index);
    }

    public static long stationId(int index) {
        return 1000L + index; // Mandatory offset of 1000
    }

    public static double measured(int index) {
        long m = mix(index, 7L) % 90000L;
        return 10.0 + (m / 1000.0);
    }

    public static Instant takenAt(int index) {
        long seconds = mix(index, 11L) % 7776000L; // 90 days in seconds
        return BASE.plusSeconds(seconds);
    }

    public static String metricCode(int index) {
        int mIndex = (int) (mix(index, 13L) % 12L);
        return METRICS[mIndex];
    }

    public static LocalDate installedOn(int index) {
        long days = mix(index, 17L) % 700L;
        return LocalDate.parse("2024-01-01").plusDays(days);
    }
}
