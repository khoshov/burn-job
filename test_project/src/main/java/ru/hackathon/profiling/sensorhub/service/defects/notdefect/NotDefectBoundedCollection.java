package ru.hackathon.profiling.sensorhub.service.defects.notdefect;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class NotDefectBoundedCollection {

    static final int MAX_TOP_STATIONS = 50;
    static final int MAX_RECENT_SAMPLES = 100;
    static final int MAX_EXPORT_ROWS = 10_000;

    public List<String> getTopStationCodes(List<String> allCodes, int limit) {
        int capped = Math.min(limit, MAX_TOP_STATIONS);
        List<String> sorted = new ArrayList<>(allCodes);
        sorted.sort(Comparator.comparingInt(String::length).reversed());
        return sorted.subList(0, Math.min(capped, sorted.size()));
    }

    public List<Double> getRecentAverages(List<Double> rawValues, int count) {
        int capped = Math.min(count, MAX_RECENT_SAMPLES);
        int from = Math.max(0, rawValues.size() - capped);
        List<Double> recent = new ArrayList<>(rawValues.subList(from, rawValues.size()));
        double sum = 0;
        for (double v : recent) {
            sum += v;
        }
        double avg = recent.isEmpty() ? 0.0 : sum / recent.size();
        return List.of(avg);
    }

    public List<String> exportBatchRows(List<String> rows, int requestedLimit) {
        int limit = Math.min(requestedLimit, MAX_EXPORT_ROWS);
        List<String> batch = new ArrayList<>(rows);
        return batch.stream().limit(limit).collect(Collectors.toList());
    }

    public double computePageStats(List<Double> pageValues, int pageSize) {
        int capped = Math.min(pageSize, 200);
        List<Double> window = pageValues.size() <= capped
                ? new ArrayList<>(pageValues)
                : new ArrayList<>(pageValues.subList(0, capped));
        double sum = 0;
        for (double v : window) {
            sum += v;
        }
        return sum / window.size();
    }

    public List<String> nearestNeighbors(List<String> points, int maxNeighbors) {
        int k = Math.min(maxNeighbors, 20);
        List<String> sorted = new ArrayList<>(points);
        sorted.sort(Comparator.naturalOrder());
        return sorted.size() <= k ? sorted : new ArrayList<>(sorted.subList(0, k));
    }
}
