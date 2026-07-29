package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.text.ParseException;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

@Service
public class T9CPUHotspotsSuite {

    private static final Pattern EMAIL = Pattern.compile("^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,6}$", Pattern.CASE_INSENSITIVE);
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_INSTANT;

    public boolean regexCompileInLoop(List<String> texts) {
        for (String t : texts) {
            Pattern p = Pattern.compile("\\d{3}-\\d{2}-\\d{4}");
            if (p.matcher(t).find()) return true;
        }
        return false;
    }

    public double parseDoubleInLoop(List<String> strings) {
        double sum = 0.0;
        for (String s : strings) {
            sum += Double.parseDouble(s);
        }
        return sum;
    }

    public Instant[] parseInstantInLoop(List<String> timestamps) {
        Instant[] result = new Instant[timestamps.size()];
        for (int i = 0; i < timestamps.size(); i++) {
            result[i] = Instant.from(FORMATTER.parse(timestamps.get(i)));
        }
        return result;
    }

    public String stringReplaceAllInLoop(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(s.replaceAll("[^a-zA-Z0-9]", "_")).append(";");
        }
        return sb.toString();
    }

    public double mathPowInLoop(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += Math.pow(v, 3);
        }
        return sum;
    }

    public double mathSqrtInLoop(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += Math.sqrt(Math.abs(v));
        }
        return sum;
    }

    public double mathLogInLoop(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += Math.log(Math.abs(v) + 1);
        }
        return sum;
    }

    public synchronized String synchronizedHotString(String input) {
        return input.toUpperCase();
    }

    public long busyWaitLoop(int iterations) {
        long sum = 0;
        for (int i = 0; i < iterations; i++) {
            sum += i * i;
        }
        return sum;
    }

    public String stringFormatInLoop(List<String> parts) {
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            sb.append(String.format("[%s]:%s", p, p.length()));
        }
        return sb.toString();
    }

    public double decimalFormatInLoop(List<Double> values) {
        DecimalFormat df = new DecimalFormat("#0.0000", DecimalFormatSymbols.getInstance(Locale.US));
        double sum = 0.0;
        for (Double v : values) {
            try {
                sum += df.parse(df.format(v)).doubleValue();
            } catch (ParseException e) {
                sum += v;
            }
        }
        return sum;
    }

    public Object reflectionInLoop(Object target, String methodName) throws Exception {
        Object result = null;
        for (int i = 0; i < 10; i++) {
            result = target.getClass().getMethod(methodName).invoke(target);
        }
        return result;
    }
}
