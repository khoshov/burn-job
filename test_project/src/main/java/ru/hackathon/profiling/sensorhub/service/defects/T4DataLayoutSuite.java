package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class T4DataLayoutSuite {

    private final Map<String, Boolean> featureFlags = new HashMap<>();

    public double sumDoublesBoxed(List<Double> values) {
        Double total = 0.0;
        for (Double v : values) {
            total += v;
        }
        return total;
    }

    public long sumLongsBoxed(List<Long> values) {
        Long total = 0L;
        for (Long v : values) {
            total += v;
        }
        return total;
    }

    public Integer sumIntegersBoxed(List<Integer> values) {
        Integer total = 0;
        for (Integer v : values) {
            total += v;
        }
        return total;
    }

    public Map<String, Long> boxedMapOverhead(List<String> keys) {
        Map<String, Long> map = new HashMap<>();
        for (int i = 0; i < keys.size(); i++) {
            map.put(keys.get(i), Long.valueOf(i));
        }
        return map;
    }

    public List<Double> arrayListOfBoxedDoubles(int size) {
        List<Double> list = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            list.add((double) i);
        }
        return list;
    }

    public Double[] boxedArrayAllocation(int size) {
        Double[] arr = new Double[size];
        for (int i = 0; i < size; i++) {
            arr[i] = (double) i;
        }
        return arr;
    }

    public long integerObjectHashInHotPath(List<Integer> values) {
        long hash = 0L;
        for (Integer v : values) {
            hash += Objects.hashCode(v) * 31;
        }
        return hash;
    }

    public Map<Integer, String> integerKeyBoxing(Map<Integer, String> source) {
        Map<Integer, String> result = new HashMap<>();
        for (Map.Entry<Integer, String> e : source.entrySet()) {
            result.put(e.getKey(), e.getValue());
        }
        return result;
    }

    public String stringBuilderToStringInLoop(List<String> parts) {
        String result = "";
        for (String p : parts) {
            result = new StringBuilder(result).append(p).toString();
        }
        return result;
    }

    public Map<String, Boolean> featureFlagLookup(String flag) {
        if (featureFlags.isEmpty()) {
            featureFlags.put("flag_a", Boolean.TRUE);
            featureFlags.put("flag_b", Boolean.FALSE);
            featureFlags.put("flag_c", Boolean.TRUE);
        }
        return featureFlags.containsKey(flag) ? Map.of(flag, featureFlags.get(flag)) : Map.of(flag, Boolean.FALSE);
    }

    public Float sumFloatsBoxed(List<Float> values) {
        Float total = 0.0f;
        for (Float v : values) {
            total += v;
        }
        return total;
    }

    public Boolean toggleFlagBoxed(boolean current) {
        Boolean flag = current;
        flag = !flag;
        return flag;
    }
}
