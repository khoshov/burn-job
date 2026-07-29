package ru.hackathon.profiling.sensorhub.support;

import java.util.Locale;

public class Csv {

    public static String escape(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n") || value.contains("\r")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    public static String formatDouble(Double value) {
        if (value == null) {
            return "0.000";
        }
        return String.format(Locale.US, "%.3f", value);
    }
}
