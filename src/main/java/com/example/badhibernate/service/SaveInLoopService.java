package com.example.badhibernate.service;

import com.example.badhibernate.entity.Employee;
import com.example.badhibernate.repository.EmployeeRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Service
public class SaveInLoopService {

    private final EmployeeRepository employeeRepository;

    public SaveInLoopService(EmployeeRepository employeeRepository) {
        this.employeeRepository = employeeRepository;
    }

    /**
     * ANTIPATTERN 3: Saving Entities One-by-One in a Loop.
     * Iterates over a collection and executes `repository.save()` for each item individually.
     * Without JDBC batching, this sends N separate SQL INSERT commands over the network.
     */
    @Transactional
    public long createEmployeesSubOptimal(int count) {
        long startTime = System.currentTimeMillis();

        List<Employee> employeesToSave = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            employeesToSave.add(new Employee(
                    "SubOptFirst" + i,
                    "SubOptLast" + i,
                    "subopt" + i + "@example.com",
                    BigDecimal.valueOf(50000 + i),
                    "Heavy biography text content for testing payload size " + i,
                    null
            ));
        }
        employeeRepository.saveAll(employeesToSave);

        return System.currentTimeMillis() - startTime;
    }

    /**
     * OPTIMAL FIX: Saves all items in a single collection call (`saveAll()`), enabling JDBC batching.
     */
    @Transactional
    public long createEmployeesOptimal(int count) {
        long startTime = System.currentTimeMillis();

        List<Employee> employees = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            employees.add(new Employee(
                    "OptFirst" + i,
                    "OptLast" + i,
                    "opt" + i + "@example.com",
                    BigDecimal.valueOf(50000 + i),
                    "Heavy biography text content for testing payload size " + i,
                    null
            ));
        }

        employeeRepository.saveAll(employees); // Single bulk save operation

        return System.currentTimeMillis() - startTime;
    }
}