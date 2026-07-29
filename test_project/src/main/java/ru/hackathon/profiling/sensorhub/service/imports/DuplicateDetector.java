package ru.hackathon.profiling.sensorhub.service.imports;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DuplicateDetector {

    private final Set<String> seen = new HashSet<>();
    private final List<String> duplicatesInOrder = new ArrayList<>();

    public boolean process(String key) {
        if (!seen.add(key)) {
            if (!duplicatesInOrder.contains(key)) {
                duplicatesInOrder.add(key);
            }
            return true;
        }
        return false;
    }

    public List<String> getDuplicates() {
        return duplicatesInOrder;
    }
}
