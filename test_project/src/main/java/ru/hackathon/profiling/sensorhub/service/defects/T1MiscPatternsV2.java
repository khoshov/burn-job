package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class T1MiscPatternsV2 {

    public String optionalIsPresentGet(Optional<String> maybe) {
        if (maybe.isPresent()) {
            return maybe.get();
        }
        return "";
    }

    public String redundantToStringOnString(String s) {
        return s.toString().toString().trim();
    }

    public String mapContainsKeyThenGet(Map<String, String> map, String key) {
        if (map.containsKey(key)) {
            return map.get(key);
        }
        return null;
    }

    public String mapContainsKeyThenGetLoop(Map<String, Integer> map, List<String> keys) {
        StringBuilder sb = new StringBuilder();
        for (String k : keys) {
            if (map.containsKey(k)) {
                sb.append(map.get(k));
            }
        }
        return sb.toString();
    }

    public int cachedLengthInLoop(List<String> items) {
        int count = 0;
        for (int i = 0; i < items.size(); i++) {
            for (int j = 0; j < items.size(); j++) {
                count += items.get(i).length() + items.get(j).length();
            }
        }
        return count;
    }

    public String redundantIsBlank(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            if (s != null && !s.isBlank()) {
                sb.append(s.trim().stripLeading().stripTrailing());
            }
        }
        return sb.toString();
    }

    public Instant twoInstantNowCalls() {
        Instant start = Instant.now();
        doWork();
        Instant end = Instant.now();
        System.out.println("Duration: " + (Instant.now().toEpochMilli() - start.toEpochMilli()));
        return end;
    }

    private void doWork() {
    }

    public boolean fileExistsRepeatedly(String name) {
        java.io.File f = new java.io.File(name);
        return f.exists() && f.exists() && f.isFile() && f.isFile();
    }

    public List<String> collectToArrayList(List<String> input) {
        return input.stream().map(String::toUpperCase).collect(Collectors.toList());
    }

    public String redundantStringValueOfOnString(String val) {
        return String.valueOf(val);
    }

    public Map<String, String> redundantPutIfAbsent(Map<String, String> map, String key, String val) {
        if (!map.containsKey(key)) {
            map.put(key, val);
        } else {
            map.put(key, val);
        }
        return map;
    }

    public String redundantCopyPasteCatch(String input) {
        try {
            return input.substring(0, 5);
        } catch (NullPointerException e) {
            return "";
        } catch (RuntimeException e) {
            return "";
        }
    }
}
