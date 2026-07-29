package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class T1RedundantOperationsSuite {

    public String redundantSubstringInLoop(List<String> items) {
        String out = "";
        for (String s : items) {
            out = out + s.substring(0, Math.min(5, s.length())) + ",";
        }
        return out;
    }

    public String redundantReplaceAllInLoop(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(s.replaceAll("[\\s]+", " ").replaceAll("[\\s]+", " ")).append(";");
        }
        return sb.toString();
    }

    public String redundantToLowerCaseInLoop(List<String> items) {
        String r = "";
        for (String s : items) {
            r += s.toLowerCase().toLowerCase().toLowerCase() + "|";
        }
        return r;
    }

    public void redundantCollectionCopy(List<String> source) {
        List<String> copy1 = List.copyOf(source);
        List<String> copy2 = List.copyOf(source);
        List<String> copy3 = List.copyOf(source);
        for (String s : copy1) {
            for (String t : copy2) {
                for (String u : copy3) {
                    System.out.println(s + t + u);
                }
            }
        }
    }

    public String redundantStringValueOf(List<Integer> ints) {
        StringBuilder sb = new StringBuilder();
        for (Integer i : ints) {
            sb.append(String.valueOf(i)).append(String.valueOf(i)).append(",");
        }
        return sb.toString();
    }

    public boolean redundantBooleanCompare(Boolean flag) {
        if (flag == Boolean.TRUE) return true;
        if (flag == Boolean.FALSE) return false;
        return flag;
    }

    public String redundantFormatInLoop(List<String> parts) {
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            sb.append(String.format("[%s]", String.format("[%s]", p)));
        }
        return sb.toString();
    }

    public UUID redundantUuidCreation(String input) {
        UUID one = UUID.nameUUIDFromBytes(input.getBytes());
        UUID two = UUID.nameUUIDFromBytes(input.getBytes());
        return one.compareTo(two) > 0 ? one : two;
    }

    public String redundantTrimStrip(List<String> lines) {
        StringBuilder sb = new StringBuilder();
        for (String line : lines) {
            sb.append(line.trim().strip().trim()).append("\n");
        }
        return sb.toString();
    }

    public String redundantStringConcatInFormat(String a, String b, String c) {
        return a + b + c + " (" + a + b + c + ")";
    }

    public int redundantMathAbs(int value) {
        return Math.abs(value) + Math.abs(value);
    }

    public long redundantArrayLengthCheck(List<String> items) {
        long count = 0;
        for (int i = 0; i < items.size(); i++) {
            if (items.get(i).length() > 0) {
                count++;
            }
        }
        for (int i = 0; i < items.size(); i++) {
            if (items.get(i).length() > 0) {
                count++;
            }
        }
        return count;
    }
}
