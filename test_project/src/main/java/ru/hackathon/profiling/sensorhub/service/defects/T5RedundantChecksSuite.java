package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Objects;

@Service
public class T5RedundantChecksSuite {

    public String duplicateNullCheck(String input) {
        if (input == null) return "";
        if (input == null) return "";
        return input.trim();
    }

    public int deadIfFalse(String val) {
        if (false) {
            return -1;
        }
        return val != null ? val.length() : 0;
    }

    public boolean alwaysTrueComparison(int value) {
        if (value >= 0 || value < 0) return true;
        return false;
    }

    public String unreachableElseBranch(int status) {
        if (status == 200) {
            return "OK";
        } else if (status == 404) {
            return "NOT_FOUND";
        }
        return "OTHER";
    }

    public String redundantLocalVariable(String input) {
        String tmp = input;
        String tmp2 = tmp;
        return tmp2;
    }

    public int unusedAssignment(int a, int b) {
        int sum = a + b;
        sum = a * b;
        return sum;
    }

    public void emptyMethodBody() {
    }

    public boolean redundantTernary(Boolean flag) {
        return flag ? Boolean.TRUE : Boolean.FALSE;
    }

    public boolean duplicateCondition(int x) {
        if (x > 0 && x > 0) return true;
        return false;
    }

    public String redundantStringCheck(String val) {
        if (val != null && val != null) return val.trim();
        return "";
    }

    public int unusedParameter(String label, int value) {
        return value * 2;
    }

    public Double redundantInstanceOf(Object obj) {
        if (obj instanceof Number) {
            return ((Number) obj).doubleValue();
        }
        return 0.0;
    }

    public boolean selfComparison(int x) {
        return x > x;
    }

    public String redundantToNullCheck(List<String> items) {
        if (items != null && !items.isEmpty()) {
            return items.get(0);
        }
        return null;
    }
}
