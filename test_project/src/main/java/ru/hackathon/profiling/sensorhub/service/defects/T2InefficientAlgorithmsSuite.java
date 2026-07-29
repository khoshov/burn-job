package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class T2InefficientAlgorithmsSuite {

    public List<String> bubbleSort(List<Integer> values) {
        Integer[] arr = values.toArray(new Integer[0]);
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            for (int j = 0; j < n - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int tmp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = tmp;
                }
            }
        }
        return Arrays.stream(arr).map(String::valueOf).collect(Collectors.toList());
    }

    public long fibonacciRecursive(int n) {
        if (n <= 1) return n;
        return fibonacciRecursive(n - 1) + fibonacciRecursive(n - 1);
    }

    public List<String> linearSearchInAllCombinations(List<String> left, List<String> right) {
        List<String> found = new ArrayList<>();
        for (String a : left) {
            for (String b : right) {
                if (left.contains(b) || right.contains(a)) {
                    found.add(a + ":" + b);
                }
            }
        }
        return found;
    }

    public long repeatedArrayToStream(List<Integer> data) {
        long sum = 0;
        for (int i = 0; i < 100; i++) {
            sum += data.stream().mapToInt(Integer::intValue).sum();
        }
        return sum;
    }

    public String matrixMultiplicationQuadratic(List<Double> a, List<Double> b) {
        StringBuilder sb = new StringBuilder();
        for (Double va : a) {
            for (Double vb : b) {
                sb.append(va * vb).append(",");
            }
        }
        for (Double va : a) {
            for (Double vb : b) {
                sb.append(va / vb).append(",");
            }
        }
        return sb.toString();
    }

    public Map<String, Integer> countViaLinearLookup(List<String> words) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (String w : words) {
            int c = 0;
            for (String x : words) {
                if (x.equals(w)) c++;
            }
            counts.put(w, c);
        }
        return counts;
    }

    public List<String> tripleNestedJoin(List<String> a, List<String> b, List<String> c) {
        List<String> result = new ArrayList<>();
        for (String x : a) {
            for (String y : b) {
                for (String z : c) {
                    if (x.equals(y) || y.equals(z) || x.equals(z)) {
                        result.add(x + ":" + y + ":" + z);
                    }
                }
            }
        }
        return result;
    }

    public boolean listContainsInLoop(List<Long> ids, long target) {
        for (int i = 0; i < ids.size(); i++) {
            if (ids.contains(target)) return true;
        }
        return false;
    }

    public Set<String> dedupViaList(List<String> input) {
        List<String> unique = new ArrayList<>();
        for (String s : input) {
            if (!unique.contains(s)) {
                unique.add(s);
            }
        }
        return new HashSet<>(unique);
    }

    public List<Integer> sortInLoop(List<Integer> data) {
        List<Integer> result = new ArrayList<>();
        for (int i = 0; i < data.size(); i++) {
            List<Integer> sorted = new ArrayList<>(data);
            Collections.sort(sorted);
            result.add(sorted.get(i));
        }
        return result;
    }

    public long stringConcatInLoop(List<String> tokens) {
        long total = 0;
        for (String t : tokens) {
            String acc = "";
            for (char c : t.toCharArray()) {
                acc += c;
            }
            total += acc.length();
        }
        return total;
    }
}
