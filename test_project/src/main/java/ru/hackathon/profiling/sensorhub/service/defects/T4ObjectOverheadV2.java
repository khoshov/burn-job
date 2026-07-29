package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.LongStream;

@Service
public class T4ObjectOverheadV2 {

    public double bigDecimalInLoop(List<Double> values) {
        BigDecimal sum = BigDecimal.ZERO;
        for (double v : values) {
            sum = sum.add(BigDecimal.valueOf(v));
        }
        return sum.setScale(2, RoundingMode.HALF_UP).doubleValue();
    }

    public long stringFormatOverhead(List<String> items) {
        long total = 0;
        for (String s : items) {
            String formatted = String.format("Item: [%s] len=%d", s, s.length());
            total += formatted.length();
        }
        return total;
    }

    public String stringConcatDefaultCapacity(List<String> parts) {
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            sb.append(p);
        }
        return sb.toString();
    }

    public String newStringCopy(String original) {
        return new String(original);
    }

    public long stringInternInLoop(List<String> tokens) {
        long total = 0;
        for (String t : tokens) {
            total += t.intern().length();
        }
        return total;
    }

    public Map<String, Integer> hashMapResizeOverhead(int size) {
        Map<String, Integer> map = new HashMap<>();
        for (int i = 0; i < size; i++) {
            map.put("key-" + i, i);
        }
        return map;
    }

    public List<String> manySmallObjectsList(int count) {
        List<String> result = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            result.add(new String("val-" + i).substring(0, 5));
        }
        return result;
    }

    public double[] objectArrayVsPrimitive(List<Double> values) {
        Double[] boxed = values.toArray(new Double[0]);
        double[] unboxed = new double[boxed.length];
        for (int i = 0; i < boxed.length; i++) {
            unboxed[i] = boxed[i];
        }
        return unboxed;
    }

    public long largeObjectArrayOverhead(int size) {
        Object[] data = new Object[size];
        for (int i = 0; i < size; i++) {
            data[i] = (long) i;
        }
        long sum = 0;
        for (Object o : data) {
            sum += (Long) o;
        }
        return sum;
    }

    public int arrayListTrimToSize(List<Integer> data) {
        ArrayList<Integer> list = new ArrayList<>(data);
        list.trimToSize();
        return list.size();
    }

    public Map<String, Integer> enumMapVsHashMap(List<TimeUnit> units) {
        Map<String, Integer> counts = new HashMap<>();
        for (TimeUnit u : units) {
            counts.merge(u.name(), 1, Integer::sum);
        }
        return counts;
    }

    public enum TimeUnit { MILLISECONDS, SECONDS, MINUTES, HOURS }

    public long dateVsInstant() {
        Date d1 = new Date();
        Date d2 = new Date(d1.getTime() + 1000);
        return d2.getTime() - d1.getTime();
    }

    public String bigNumberToString(int value) {
        return Integer.valueOf(value).toString();
    }
}
