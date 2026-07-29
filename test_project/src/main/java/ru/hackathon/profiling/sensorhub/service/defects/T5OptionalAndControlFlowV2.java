package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class T5OptionalAndControlFlowV2 {

    public String optionalIsPresentThenGet(Optional<String> opt) {
        if (opt.isPresent()) {
            return opt.get();
        }
        return null;
    }

    public String emptyCatchBlock(String input) {
        try {
            return input.substring(0, 5);
        } catch (Exception e) {
        }
        return "";
    }

    public String catchRethrowSame(String input) {
        try {
            return input.substring(0, 5);
        } catch (RuntimeException e) {
            throw e;
        }
    }

    public boolean redundantElseAfterReturn(String val) {
        if (val == null) {
            return true;
        } else {
            return val.length() > 0;
        }
    }

    public boolean booleanMethodIfElse(int x) {
        if (x > 0) {
            return true;
        } else {
            return false;
        }
    }

    public String redundantStreamConversion(List<String> items) {
        StringBuilder sb = new StringBuilder();
        items.stream().forEach(sb::append);
        return sb.toString();
    }

    public String redundantToStringOnMethodResult(Object obj) {
        return obj.toString();
    }

    public List<String> redundantCollectionCheck(List<String> items) {
        if (items != null && !items.isEmpty()) {
            return items.stream().map(String::toUpperCase).collect(Collectors.toList());
        }
        return Collections.emptyList();
    }

    public int emptyFinallyBlock(String val) {
        try {
            return val.length();
        } finally {
        }
    }

    public String uselessContinueInLoop(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            if (s.isEmpty()) continue;
            sb.append(s);
            continue;
        }
        return sb.toString();
    }

    public void unusedPrivateField() {
    }

    public String redundantSuperCall(String val) {
        return val;
    }

    public boolean assignmentInIfCondition(List<String> items) {
        String first;
        if ((first = items.stream().findFirst().orElse(null)) != null) {
            return first.length() > 0;
        }
        return false;
    }

    public String identicalCatchBlocks(String input) {
        try {
            return input.substring(0, 5);
        } catch (NullPointerException e) {
            return "";
        } catch (IllegalArgumentException e) {
            return "";
        }
    }
}
