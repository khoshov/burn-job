package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;

@Service
public class T2CorrectPatterns {

    public List<String> hashSetLookup(List<String> stations, List<String> targetCodes) {
        Set<String> targetSet = new HashSet<>(targetCodes);
        List<String> matched = new ArrayList<>();
        for (String s : stations) {
            if (targetSet.contains(s)) {
                matched.add(s);
            }
        }
        return matched;
    }

    public Map<String, Integer> hashMapWordCount(List<String> words) {
        Map<String, Integer> counts = new HashMap<>();
        for (String w : words) {
            counts.merge(w, 1, Integer::sum);
        }
        return counts;
    }

    public long arrayListSum(List<Integer> data) {
        long sum = 0;
        for (int v : data) {
            sum += v;
        }
        return sum;
    }

    public long cachedStreamSum(List<Integer> data) {
        return data.stream().mapToInt(Integer::intValue).sum();
    }

    public String singlePassMatrix(List<Double> a, List<Double> b) {
        StringBuilder sb = new StringBuilder(a.size() * b.size() * 8);
        for (double va : a) {
            for (double vb : b) {
                sb.append(va * vb).append(",");
            }
        }
        return sb.toString();
    }

    public List<String> hashJoin(List<String> a, List<String> b) {
        Set<String> setB = new HashSet<>(b);
        return a.stream().filter(setB::contains).collect(Collectors.toList());
    }

    public String tripleJoinEfficient(List<String> a, List<String> b, List<String> c) {
        Set<String> all = new HashSet<>();
        all.addAll(a);
        all.addAll(b);
        all.addAll(c);
        return String.join(":", all);
    }

    public boolean hashSetContains(List<Long> ids, long target) {
        Set<Long> idSet = new HashSet<>(ids);
        return idSet.contains(target);
    }

    public Set<String> dedupViaSet(List<String> input) {
        return new LinkedHashSet<>(input);
    }

    public List<Integer> singleSort(List<Integer> data) {
        List<Integer> sorted = new ArrayList<>(data);
        Collections.sort(sorted);
        return sorted;
    }

    public String stringBuilderInLoop(List<String> tokens) {
        StringBuilder sb = new StringBuilder();
        for (String t : tokens) {
            sb.append(t);
        }
        return sb.toString();
    }

    public long fibonacciMemoized(int n) {
        if (n <= 1) return n;
        long[] cache = new long[n + 1];
        cache[0] = 0; cache[1] = 1;
        for (int i = 2; i <= n; i++) {
            cache[i] = cache[i - 1] + cache[i - 2];
        }
        return cache[n];
    }
}
