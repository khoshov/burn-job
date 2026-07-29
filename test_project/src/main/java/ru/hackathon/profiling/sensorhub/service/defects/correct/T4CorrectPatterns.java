package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class T4CorrectPatterns {

    public double sumDoublesPrimitive(List<Double> values) {
        double total = 0.0;
        for (double v : values) {
            total += v;
        }
        return total;
    }

    public long sumLongsPrimitive(List<Long> values) {
        long total = 0L;
        for (long v : values) {
            total += v;
        }
        return total;
    }

    public int sumIntegersPrimitive(List<Integer> values) {
        int total = 0;
        for (int v : values) {
            total += v;
        }
        return total;
    }

    public Map<String, Integer> intMapNoBoxing(List<String> keys) {
        Map<String, Integer> map = new HashMap<>(keys.size());
        int i = 0;
        for (String k : keys) {
            map.put(k, i++);
        }
        return map;
    }

    public double[] primitiveArray(int size) {
        double[] arr = new double[size];
        for (int i = 0; i < size; i++) {
            arr[i] = i;
        }
        return arr;
    }

    public int hashCodeInt(int value) {
        return Integer.hashCode(value) * 31;
    }

    public long integerKeyMapEfficient(Map<String, Integer> source) {
        long total = 0;
        for (int v : source.values()) {
            total += v;
        }
        return total;
    }

    public String efficientStringConcat(List<String> parts) {
        if (parts.isEmpty()) return "";
        if (parts.size() == 1) return parts.get(0);
        StringBuilder sb = new StringBuilder(parts.stream().mapToInt(String::length).sum());
        for (String p : parts) {
            sb.append(p);
        }
        return sb.toString();
    }

    public boolean toggleBoolean(boolean current) {
        return !current;
    }

    public BigDecimal bigDecimalOnce(BigDecimal value) {
        return value.setScale(2, BigDecimal.ROUND_HALF_UP);
    }

    public String singleFormat(String s) {
        return "Item: [" + s + "] len=" + s.length();
    }

    public int cachedStringIntern(String t) {
        return t.length();
    }

    public Map<String, Integer> hashMapWithCapacity(int expectedSize) {
        return new HashMap<>(expectedSize * 4 / 3 + 1);
    }

    public String integerToString(int value) {
        return Integer.toString(value);
    }
}
