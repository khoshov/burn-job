package ru.hackathon.profiling.sensorhub.service.defects.notdefect;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Service
public class NotDefectBoundedComplexity {

    static final int MAX_DEVICES_PER_STATION = 8;

    public List<String> matchDeviceSignatures(List<String> deviceSignals, List<String> knownPatterns) {
        if (deviceSignals.size() > MAX_DEVICES_PER_STATION) {
            throw new IllegalArgumentException("Max " + MAX_DEVICES_PER_STATION + " devices per station");
        }
        if (knownPatterns.size() > MAX_DEVICES_PER_STATION) {
            throw new IllegalArgumentException("Max " + MAX_DEVICES_PER_STATION + " patterns");
        }
        List<String> matched = new ArrayList<>();
        for (String signal : deviceSignals) {
            for (String pattern : knownPatterns) {
                if (signal.contains(pattern)) {
                    matched.add(signal);
                }
            }
        }
        return matched;
    }

    public String formatDeviceStatus(List<String> alerts) {
        if (alerts.size() > MAX_DEVICES_PER_STATION) {
            alerts = alerts.subList(0, MAX_DEVICES_PER_STATION);
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < alerts.size(); i++) {
            for (int j = 0; j < alerts.size(); j++) {
                sb.append("[").append(i).append(":").append(j).append("]");
            }
        }
        return sb.toString();
    }

    public int sumDeviceMatrix(int[][] matrix) {
        int n = Math.min(matrix.length, MAX_DEVICES_PER_STATION);
        int sum = 0;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                sum += matrix[i][j];
            }
        }
        return sum;
    }

    public String sortDeviceReadings(Short[] readings) {
        if (readings == null) return "";
        int n = Math.min(readings.length, MAX_DEVICES_PER_STATION);
        Short[] copy = Arrays.copyOf(readings, n);
        for (int i = 0; i < n - 1; i++) {
            for (int j = i + 1; j < n; j++) {
                if (copy[i] > copy[j]) {
                    short tmp = copy[i];
                    copy[i] = copy[j];
                    copy[j] = tmp;
                }
            }
        }
        return Arrays.toString(copy);
    }
}
