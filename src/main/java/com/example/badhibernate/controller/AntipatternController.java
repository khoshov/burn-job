package com.example.badhibernate.controller;

import com.example.badhibernate.dto.DepartmentDto;
import com.example.badhibernate.dto.EmployeeSimpleDto;
import com.example.badhibernate.dto.OrderSummaryDto;
import com.example.badhibernate.service.FullEntityFetchService;
import com.example.badhibernate.service.InMemoryFilterService;
import com.example.badhibernate.service.NPlusOneService;
import com.example.badhibernate.service.SaveInLoopService;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/demo")
public class AntipatternController {

    private final NPlusOneService nPlusOneService;
    private final InMemoryFilterService inMemoryFilterService;
    private final SaveInLoopService saveInLoopService;
    private final FullEntityFetchService fullEntityFetchService;

    public AntipatternController(
            NPlusOneService nPlusOneService,
            InMemoryFilterService inMemoryFilterService,
            SaveInLoopService saveInLoopService,
            FullEntityFetchService fullEntityFetchService) {
        this.nPlusOneService = nPlusOneService;
        this.inMemoryFilterService = inMemoryFilterService;
        this.saveInLoopService = saveInLoopService;
        this.fullEntityFetchService = fullEntityFetchService;
    }

    // 1. N+1 SELECTS DEMO
    @GetMapping("/n-plus-one/bad")
    public List<DepartmentDto> getNPlusOneSubOptimal() {
        return nPlusOneService.getDepartmentsSubOptimal();
    }

    @GetMapping("/n-plus-one/good")
    public List<DepartmentDto> getNPlusOneOptimal() {
        return nPlusOneService.getDepartmentsOptimal();
    }

    // 2. IN-MEMORY FILTERING DEMO
    @GetMapping("/in-memory-filter/bad")
    public List<OrderSummaryDto> getInMemoryFilterSubOptimal(
            @RequestParam(defaultValue = "SHIPPED") String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return inMemoryFilterService.getOrdersByStatusSubOptimal(status, page, size);
    }

    @GetMapping("/in-memory-filter/good")
    public Page<OrderSummaryDto> getInMemoryFilterOptimal(
            @RequestParam(defaultValue = "SHIPPED") String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return inMemoryFilterService.getOrdersByStatusOptimal(status, page, size);
    }

    // 3. SAVE IN LOOP DEMO
    @PostMapping("/save-in-loop/compare")
    public Map<String, Object> compareSaveInLoop(@RequestParam(defaultValue = "200") int count) {
        long badMs = saveInLoopService.createEmployeesSubOptimal(count);
        long goodMs = saveInLoopService.createEmployeesOptimal(count);

        Map<String, Object> result = new HashMap<>();
        result.put("itemCount", count);
        result.put("subOptimalTimeMs", badMs);
        result.put("optimalTimeMs", goodMs);
        result.put("speedupFactor", String.format("%.2fx faster", (double) badMs / Math.max(1, goodMs)));
        return result;
    }

    // 4. FULL ENTITY FETCH VS PROJECTION DEMO
    @GetMapping("/entity-fetch/bad")
    public List<EmployeeSimpleDto> getFullEntitySubOptimal() {
        return fullEntityFetchService.getEmployeesSubOptimal();
    }

    @GetMapping("/entity-fetch/good")
    public List<EmployeeSimpleDto> getFullEntityOptimal() {
        return fullEntityFetchService.getEmployeesOptimal();
    }
}
