package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.regex.Pattern;
import java.util.stream.DoubleStream;

@Service
public class T9CorrectPatterns {

    private static final Pattern EMAIL_PATTERN = Pattern.compile(
            "^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,6}$", Pattern.CASE_INSENSITIVE);
    private static final Pattern PHONE_PATTERN = Pattern.compile("\\d{3}-\\d{2}-\\d{4}");
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_INSTANT;
    private static final DecimalFormat DF = new DecimalFormat("#0.0000",
            DecimalFormatSymbols.getInstance(Locale.US));
    private static final Lock LOCK = new ReentrantLock();

    public boolean regexCompileOnce(List<String> texts) {
        for (String t : texts) {
            if (PHONE_PATTERN.matcher(t).find()) return true;
        }
        return false;
    }

    public double parseDoubleOnce(List<String> strings) {
        double sum = 0.0;
        for (String s : strings) {
            sum += Double.parseDouble(s);
        }
        return sum;
    }

    public Instant[] parseInstantOnce(List<String> timestamps) {
        Instant[] result = new Instant[timestamps.size()];
        int i = 0;
        for (String ts : timestamps) {
            result[i++] = Instant.parse(ts);
        }
        return result;
    }

    public String replaceAllOutsideLoop(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(s).append(";");
        }
        return sb.toString().replaceAll("[^a-zA-Z0-9]", "_");
    }

    public double mathPowOnce(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += v * v * v;
        }
        return sum;
    }

    public double mathSqrtOnce(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += Math.sqrt(Math.abs(v));
        }
        return sum;
    }

    public double mathLogOnce(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += Math.log(Math.abs(v) + 1);
        }
        return sum;
    }

    public String unsynchronizedTransform(String input) {
        return input.toUpperCase();
    }

    public long nonBusyLoop(int iterations) {
        return (long) iterations * (iterations - 1) / 2;
    }

    public String stringConcatOnce(List<String> parts) {
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            sb.append("[").append(p).append("]:").append(p.length());
        }
        return sb.toString();
    }

    public double decimalFormatOnce(Double value) {
        try {
            return DF.parse(DF.format(value)).doubleValue();
        } catch (Exception e) {
            return value;
        }
    }

    public Object reflectionOnce(Object target, String methodName) throws Exception {
        var method = target.getClass().getMethod(methodName);
        return method.invoke(target);
    }

    public long nonBusyLock() {
        if (LOCK.tryLock()) {
            try {
                return 1;
            } finally {
                LOCK.unlock();
            }
        }
        return 0;
    }

    public long longAdderPattern(List<Long> values) {
        long total = 0;
        for (long v : values) total += v;
        return total;
    }
}
