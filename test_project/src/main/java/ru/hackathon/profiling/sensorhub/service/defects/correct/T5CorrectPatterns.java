package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class T5CorrectPatterns {

    public String properNullCheck(String input) {
        if (input == null) return "";
        return input.trim();
    }

    public int properLength(String val) {
        if (val == null) return -1;
        return val.length();
    }

    public boolean properRangeCheck(int value) {
        return value >= 0;
    }

    public String properStatusCode(int status) {
        return switch (status) {
            case 200 -> "OK";
            case 404 -> "NOT_FOUND";
            default -> "OTHER";
        };
    }

    public int directReturn(int a, int b) {
        return a * b;
    }

    public void doNothing() {
    }

    public boolean directBoolean(boolean flag) {
        return flag;
    }

    public boolean singleCondition(int x) {
        return x > 0;
    }

    public String singleNullCheck(String val) {
        if (val == null) return "";
        return val.trim();
    }

    public int usedParameter(int value) {
        return value * 2;
    }

    public double properInstanceOf(Object obj) {
        if (obj instanceof Number n) {
            return n.doubleValue();
        }
        return 0.0;
    }

    public boolean properComparison(int x) {
        return x > 0;
    }

    public String properListAccess(List<String> items) {
        if (items == null || items.isEmpty()) return null;
        return items.get(0);
    }

    public String optionalProper(Optional<String> opt) {
        return opt.orElse("");
    }

    public String properCatch(String input) {
        try {
            return input.substring(0, 5);
        } catch (Exception e) {
            return "";
        }
    }
}
