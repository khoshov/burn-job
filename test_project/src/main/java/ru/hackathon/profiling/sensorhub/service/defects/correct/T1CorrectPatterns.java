package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class T1CorrectPatterns {

    public String stringBuilderInLoop(List<String> items) {
        StringBuilder sb = new StringBuilder(items.size() * 16);
        for (String s : items) {
            sb.append(s.trim()).append(",");
        }
        return sb.toString();
    }

    public String eagerOperationOnce(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(s.trim().toUpperCase()).append(",");
        }
        return sb.toString();
    }

    public Double computeOnce(List<Double> values) {
        double sum = 0.0;
        for (double v : values) {
            sum += Math.pow(v, 2) + Math.sqrt(v);
        }
        return sum;
    }

    public void queryOnce(List<String> stationCodes) {
        for (String code : stationCodes) {
            if (code != null && !code.isBlank()) {
                System.out.println(code);
            }
        }
    }

    public String singleReplace(List<String> items) {
        StringBuilder sb = new StringBuilder();
        String regex = "[\\s]+";
        for (String s : items) {
            sb.append(s.replaceAll(regex, " ")).append(";");
        }
        return sb.toString();
    }

    public String noChainedLowercase(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(s.toLowerCase()).append("|");
        }
        return sb.toString();
    }

    public void singleCollectionCopy(List<String> source) {
        List<String> copy = List.copyOf(source);
        for (String s : copy) {
            System.out.println(s);
        }
    }

    public String singleValueOf(List<Integer> ints) {
        StringBuilder sb = new StringBuilder(ints.size() * 4);
        for (int i : ints) {
            sb.append(i).append(",");
        }
        return sb.toString();
    }

    public UUID singleUuid(String input) {
        return UUID.nameUUIDFromBytes(input.getBytes());
    }

    public String singleTrim(List<String> lines) {
        StringBuilder sb = new StringBuilder(lines.size() * 80);
        for (String line : lines) {
            sb.append(line.trim()).append("\n");
        }
        return sb.toString();
    }

    public String stringConcatOnce(String a, String b, String c) {
        String combined = a + b + c;
        return combined + " (" + combined + ")";
    }

    public int mathAbsOnce(int value) {
        int abs = Math.abs(value);
        return abs + abs;
    }

    public long singleLoopCheck(List<String> items) {
        long count = 0;
        for (String s : items) {
            if (!s.isEmpty()) count++;
        }
        return count;
    }
}
