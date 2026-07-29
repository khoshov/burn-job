package ru.hackathon.profiling.sensorhub.web;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.hackathon.profiling.sensorhub.service.defects.SyntheticDefectsService;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/defects")
public class SyntheticDefectsController {

    private final SyntheticDefectsService defectsService;

    public SyntheticDefectsController(SyntheticDefectsService defectsService) {
        this.defectsService = defectsService;
    }

    @GetMapping("/t1/duplicate-op-1")
    public ResponseEntity<String> testT1Op1(@RequestParam List<String> items) {
        return ResponseEntity.ok(defectsService.t1_duplicate_op_1(items));
    }

    @GetMapping("/t1/duplicate-op-2")
    public ResponseEntity<String> testT1Op2(@RequestParam List<String> items) {
        return ResponseEntity.ok(defectsService.t1_duplicate_op_2(items));
    }

    @GetMapping("/t2/nested-loop")
    public ResponseEntity<List<String>> testT2NestedLoop(@RequestParam List<String> targetCodes) {
        return ResponseEntity.ok(defectsService.t2_nested_loop_1(List.of(), targetCodes));
    }

    @GetMapping("/t2/linear-search")
    public ResponseEntity<Boolean> testT2LinearSearch(@RequestParam List<String> names, @RequestParam List<String> targets) {
        return ResponseEntity.ok(defectsService.t2_linear_search_contains_1(names, targets));
    }

    @GetMapping("/t3/existence-full-fetch")
    public ResponseEntity<Boolean> testT3Existence(@RequestParam String code) {
        return ResponseEntity.ok(defectsService.t3_existence_full_fetch_1(code));
    }

    @GetMapping("/t4/boxed-overhead")
    public ResponseEntity<Double> testT4Boxed(@RequestParam List<Double> inputs) {
        return ResponseEntity.ok(defectsService.t4_boxed_overhead_1(inputs));
    }

    @GetMapping("/t5/null-checks")
    public ResponseEntity<String> testT5NullChecks(@RequestParam String input) {
        return ResponseEntity.ok(defectsService.t5_redundant_null_checks(input));
    }

    @GetMapping("/t6/unbatched-save")
    public ResponseEntity<String> testT6Unbatched() {
        defectsService.t6_unbatched_save_loop(List.of());
        return ResponseEntity.ok("OK");
    }

    @GetMapping("/t6/n-plus-one")
    public ResponseEntity<List<String>> testT6NPlusOne() {
        return ResponseEntity.ok(defectsService.t6_n_plus_one_lazy_load());
    }

    @GetMapping("/t7/unbounded-map")
    public ResponseEntity<String> testT7Unbounded(@RequestParam String key) {
        defectsService.t7_unbounded_map_leak(key, "data");
        return ResponseEntity.ok("OK");
    }

    @GetMapping("/t8/in-memory-filtering")
    public ResponseEntity<Integer> testT8InMemoryFilter() {
        return ResponseEntity.ok(defectsService.t8_in_memory_filtering(Instant.now()).size());
    }

    @GetMapping("/t9/regex-compile")
    public ResponseEntity<Boolean> testT9Regex(@RequestParam String text) {
        return ResponseEntity.ok(defectsService.t9_regex_compile_in_loop(text));
    }
}
