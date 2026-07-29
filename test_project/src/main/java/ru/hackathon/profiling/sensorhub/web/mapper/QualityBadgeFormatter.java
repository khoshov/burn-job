package ru.hackathon.profiling.sensorhub.web.mapper;

public class QualityBadgeFormatter {

    public static String formatBadge(String quality) {
        if (quality == null) {
            return "[G]";
        }
        return switch (quality.toUpperCase()) {
            case "GOOD", "1" -> "[G]";
            case "BAD", "0" -> "[B]";
            case "UNCERTAIN" -> "[U]";
            default -> "[" + quality.substring(0, Math.min(1, quality.length())).toUpperCase() + "]";
        };
    }
}
