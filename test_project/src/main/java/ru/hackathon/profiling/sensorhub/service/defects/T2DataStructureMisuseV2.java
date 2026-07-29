package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class T2DataStructureMisuseV2 {

    public String linkedListRandomAccess(List<String> items) {
        List<String> list = new LinkedList<>(items);
        String result = "";
        for (int i = 0; i < list.size(); i++) {
            result += list.get(i);
        }
        return result;
    }

    public String linkedListInsertAtEnd(List<String> items) {
        List<String> list = new LinkedList<>();
        for (String s : items) {
            list.add(0, s);
        }
        StringBuilder sb = new StringBuilder();
        for (String s : list) {
            sb.append(s);
        }
        return sb.toString();
    }

    public String copyOnWriteWriteHot(List<String> items) {
        List<String> list = new CopyOnWriteArrayList<>();
        for (String s : items) {
            list.add(s);
        }
        return String.join(",", list);
    }

    public String hashtableInsteadOfHashMap(Map<String, String> input) {
        Hashtable<String, String> table = new Hashtable<>(input);
        StringBuilder sb = new StringBuilder();
        Enumeration<String> keys = table.keys();
        while (keys.hasMoreElements()) {
            sb.append(table.get(keys.nextElement()));
        }
        return sb.toString();
    }

    public String treeMapWithoutComparator(Map<String, String> data) {
        TreeMap<String, String> sorted = new TreeMap<>(data);
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, String> e : sorted.entrySet()) {
            sb.append(e.getValue());
        }
        return sb.toString();
    }

    public String stringBufferInsteadOfBuilder(List<String> parts) {
        StringBuffer buf = new StringBuffer();
        for (String p : parts) {
            buf.append(p);
        }
        return buf.toString();
    }

    public String streamDistinctOnLargeData(List<String> data) {
        return data.stream().distinct().sorted().collect(ArrayList::new, ArrayList::add, ArrayList::addAll).toString();
    }

    public long concurrentHashMapReadHeavy(Map<String, Long> map, List<String> keys) {
        long total = 0;
        synchronized (map) {
            for (String k : keys) {
                Long v = map.get(k);
                if (v != null) total += v;
            }
        }
        return total;
    }

    public long priorityQueueWithComplexComparator(List<Map.Entry<String, Long>> entries) {
        PriorityQueue<Map.Entry<String, Long>> pq = new PriorityQueue<>(
                (a, b) -> {
                    int cmp = Long.compare(a.getValue(), b.getValue());
                    if (cmp == 0) cmp = a.getKey().compareTo(b.getKey());
                    if (cmp == 0) cmp = Integer.compare(a.getKey().hashCode(), b.getKey().hashCode());
                    return cmp;
                }
        );
        pq.addAll(entries);
        long total = 0;
        while (!pq.isEmpty()) {
            total += pq.poll().getValue();
        }
        return total;
    }

    public Set<String> treeSetWithSlowComparator(List<String> items) {
        Set<String> set = new TreeSet<>((a, b) -> {
            int cmp = Integer.compare(a.length(), b.length());
            if (cmp == 0) cmp = a.compareTo(b);
            return cmp;
        });
        set.addAll(items);
        return set;
    }

    public String stringSplitInLoop(List<String> lines) {
        StringBuilder sb = new StringBuilder();
        for (String line : lines) {
            String[] parts = line.split(",");
            for (String p : parts) {
                sb.append(p.trim());
            }
        }
        return sb.toString();
    }

    public int integerToStringInLoop(List<Integer> values) {
        int total = 0;
        for (int v : values) {
            total += Integer.toString(v).length();
        }
        return total;
    }
}
