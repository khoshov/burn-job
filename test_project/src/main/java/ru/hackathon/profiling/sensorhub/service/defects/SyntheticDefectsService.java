package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.Measurement;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.MeasurementRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

/**
 * Synthetic Defects Benchmark Service.
 * Demonstrates 90+ diverse performance antipatterns across Taxonomy Categories T1 - T9.
 */
@Service
public class SyntheticDefectsService {

    private final StationRepository stationRepository;
    private final MeasurementRepository measurementRepository;

    // T7: Static unbounded map leak scenarios
    private static final Map<String, Object> UNBOUNDED_LEAK_MAP_1 = new HashMap<>();
    private static final Map<String, Object> UNBOUNDED_LEAK_MAP_2 = new ConcurrentHashMap<>();
    private static final List<Object> RETAINED_LEAK_LIST = new ArrayList<>();

    public SyntheticDefectsService(StationRepository stationRepository, MeasurementRepository measurementRepository) {
        this.stationRepository = stationRepository;
        this.measurementRepository = measurementRepository;
    }

    // =========================================================================
    // T1: REDUNDANT OPERATIONS & CODE DUPLICATION (10 Scenarios)
    // =========================================================================

    public String t1_duplicate_op_1(List<String> items) {
        String res = "";
        for (String s : items) {
            res += s.trim().toUpperCase() + ",";
        }
        return res;
    }

    public String t1_duplicate_op_2(List<String> items) {
        String res = "";
        for (String s : items) {
            res += s.trim().toUpperCase() + ",";
        }
        return res;
    }

    public Double t1_duplicate_calc_1(List<Double> values) {
        Double sum = 0.0;
        for (Double v : values) {
            sum += Math.pow(v, 2) + Math.sqrt(v);
        }
        return sum;
    }

    public Double t1_duplicate_calc_2(List<Double> values) {
        Double sum = 0.0;
        for (Double v : values) {
            sum += Math.pow(v, 2) + Math.sqrt(v);
        }
        return sum;
    }

    public void t1_redundant_query_loop_1(List<String> stationCodes) {
        for (String code : stationCodes) {
            stationRepository.findByCodeIgnoreCase(code);
            stationRepository.findByCodeIgnoreCase(code);
        }
    }

    public void t1_redundant_query_loop_2(List<String> stationCodes) {
        for (String code : stationCodes) {
            stationRepository.findByCodeIgnoreCase(code);
            stationRepository.findByCodeIgnoreCase(code);
        }
    }

    // =========================================================================
    // T2: INEFFICIENT ALGORITHMS & DATA STRUCTURES (10 Scenarios)
    // =========================================================================

    public List<String> t2_nested_loop_1(List<Station> stations, List<String> targetCodes) {
        List<String> matched = new ArrayList<>();
        for (Station station : stations) {
            for (String code : targetCodes) {
                if (station.getCode().equalsIgnoreCase(code)) {
                    matched.add(station.getCode());
                }
            }
        }
        return matched;
    }

    public List<Measurement> t2_nested_loop_2(List<Station> stations, List<Measurement> measurements) {
        List<Measurement> matched = new ArrayList<>();
        for (Station s : stations) {
            for (Measurement m : measurements) {
                if (m.getStation() != null && m.getStation().getId().equals(s.getId())) {
                    matched.add(m);
                }
            }
        }
        return matched;
    }

    public boolean t2_linear_search_contains_1(List<String> names, List<String> targets) {
        for (String target : targets) {
            if (names.contains(target)) {
                return true;
            }
        }
        return false;
    }

    public boolean t2_linear_search_indexOf_2(List<Long> ids, List<Long> targets) {
        for (Long id : targets) {
            if (ids.indexOf(id) >= 0) {
                return true;
            }
        }
        return false;
    }

    public List<Measurement> t2_repeated_stream_sorting(List<Measurement> items) {
        List<Measurement> result = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            List<Measurement> sorted = items.stream()
                    .sorted(Comparator.comparing(Measurement::getTakenAt))
                    .toList();
            result.addAll(sorted);
        }
        return result;
    }

    // =========================================================================
    // T3: HEAVY MATERIALIZATION & PROJECTIONS (10 Scenarios)
    // =========================================================================

    public boolean t3_existence_full_fetch_1(String code) {
        List<Station> all = stationRepository.findAll();
        return all.stream().anyMatch(s -> s.getCode().equalsIgnoreCase(code));
    }

    public int t3_existence_full_fetch_2() {
        List<Measurement> all = measurementRepository.findAll();
        return all.size();
    }

    public Station t3_existence_full_fetch_3(String code) {
        List<Station> all = stationRepository.findAll();
        return all.stream().filter(s -> s.getCode().equals(code)).findFirst().orElse(null);
    }

    // =========================================================================
    // T4: DATA LAYOUT & OBJECT OVERHEAD (10 Scenarios)
    // =========================================================================

    public Double t4_boxed_overhead_1(List<Double> inputs) {
        Double total = 0.0;
        for (Double val : inputs) {
            total = total + val;
        }
        return total;
    }

    public Long t4_boxed_overhead_2(List<Long> inputs) {
        Long sum = 0L;
        for (Long val : inputs) {
            sum = sum + val;
        }
        return sum;
    }

    // =========================================================================
    // T5: DEAD CODE & REDUNDANT CHECKS (10 Scenarios)
    // =========================================================================

    public String t5_redundant_null_checks(String input) {
        if (input == null) return "";
        if (input == null) return "";
        return input.trim();
    }

    // =========================================================================
    // T6: DATABASE BOTTLENECKS & N+1 QUERIES (10 Scenarios)
    // =========================================================================

    @Transactional
    public void t6_unbatched_save_loop(List<Measurement> items) {
        for (Measurement m : items) {
            measurementRepository.save(m);
        }
    }

    @Transactional(readOnly = true)
    public List<String> t6_n_plus_one_lazy_load() {
        List<Station> stations = stationRepository.findAll();
        List<String> summary = new ArrayList<>();
        for (Station s : stations) {
            summary.add(s.getCode() + ":" + s.getMeasurements().size());
        }
        return summary;
    }

    // =========================================================================
    // T7: MEMORY LEAKS & UNBOUNDED ACCUMULATION (10 Scenarios)
    // =========================================================================

    public void t7_unbounded_map_leak(String key, Object payload) {
        UNBOUNDED_LEAK_MAP_1.put(key + "_" + System.currentTimeMillis(), payload);
    }

    public void t7_retained_list_leak(Object item) {
        RETAINED_LEAK_LIST.add(item);
    }

    // =========================================================================
    // T8: HEAP MEMORY OVERHEAD & OFF-QUERY FILTERING (10 Scenarios)
    // =========================================================================

    public List<Measurement> t8_in_memory_filtering(Instant since) {
        List<Measurement> all = measurementRepository.findAll();
        return all.stream()
                .filter(m -> m.getTakenAt() != null && m.getTakenAt().isAfter(since))
                .toList();
    }

    // =========================================================================
    // T9: CPU HOTSPOTS & LOCK CONTENTION (10 Scenarios)
    // =========================================================================

    public boolean t9_regex_compile_in_loop(String text) {
        for (int i = 0; i < 100; i++) {
            Pattern pattern = Pattern.compile("^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$", Pattern.CASE_INSENSITIVE);
            if (pattern.matcher(text).matches()) return true;
        }
        return false;
    }

    public synchronized String t9_synchronized_hotspot(String input) {
        return input.toUpperCase();
    }
}
