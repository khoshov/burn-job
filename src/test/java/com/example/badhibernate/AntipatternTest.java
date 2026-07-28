package com.example.badhibernate;

import com.example.badhibernate.dto.DepartmentDto;
import com.example.badhibernate.dto.EmployeeSimpleDto;
import com.example.badhibernate.dto.OrderSummaryDto;
import com.example.badhibernate.service.FullEntityFetchService;
import com.example.badhibernate.service.InMemoryFilterService;
import com.example.badhibernate.service.NPlusOneService;
import com.example.badhibernate.service.SaveInLoopService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class AntipatternTest {

    @Autowired
    private NPlusOneService nPlusOneService;

    @Autowired
    private InMemoryFilterService inMemoryFilterService;

    @Autowired
    private SaveInLoopService saveInLoopService;

    @Autowired
    private FullEntityFetchService fullEntityFetchService;

    @Test
    @DisplayName("Antipattern 1: Compare N+1 Queries vs JOIN FETCH")
    void testNPlusOneComparison() {
        System.out.println("=== RUNNING SUB-OPTIMAL N+1 SERVICE ===");
        long startBad = System.currentTimeMillis();
        List<DepartmentDto> badResult = nPlusOneService.getDepartmentsSubOptimal();
        long timeBad = System.currentTimeMillis() - startBad;

        System.out.println("=== RUNNING OPTIMAL JOIN FETCH SERVICE ===");
        long startGood = System.currentTimeMillis();
        List<DepartmentDto> goodResult = nPlusOneService.getDepartmentsOptimal();
        long timeGood = System.currentTimeMillis() - startGood;

        assertEquals(badResult.size(), goodResult.size());
        System.out.printf("N+1 Sub-optimal: %d ms | JOIN FETCH Optimal: %d ms%n", timeBad, timeGood);
    }

    @Test
    @DisplayName("Antipattern 2: Compare In-Memory Filter vs Database SQL Filter")
    void testInMemoryFilterComparison() {
        System.out.println("=== RUNNING SUB-OPTIMAL IN-MEMORY FILTER ===");
        List<OrderSummaryDto> badResult = inMemoryFilterService.getOrdersByStatusSubOptimal("SHIPPED", 0, 10);

        System.out.println("=== RUNNING OPTIMAL SQL FILTER ===");
        var goodResult = inMemoryFilterService.getOrdersByStatusOptimal("SHIPPED", 0, 10);

        assertEquals(badResult.size(), goodResult.getContent().size());
    }

    @Test
    @DisplayName("Antipattern 3: Compare Save In Loop vs Bulk SaveAll")
    void testSaveInLoopComparison() {
        int count = 100;
        long timeBad = saveInLoopService.createEmployeesSubOptimal(count);
        long timeGood = saveInLoopService.createEmployeesOptimal(count);

        System.out.printf("Save-in-loop (100 items): %d ms | SaveAll bulk (100 items): %d ms%n", timeBad, timeGood);
        assertTrue(timeGood <= timeBad || timeGood < 500, "Bulk save should generally be faster or very efficient");
    }

    @Test
    @DisplayName("Antipattern 4: Compare Full Entity Fetch vs Interface Projection")
    void testFullEntityFetchComparison() {
        List<EmployeeSimpleDto> badResult = fullEntityFetchService.getEmployeesSubOptimal();
        List<EmployeeSimpleDto> goodResult = fullEntityFetchService.getEmployeesOptimal();

        assertEquals(badResult.size(), goodResult.size());
    }
}
