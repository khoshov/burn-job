package com.example.badhibernate.service;

import com.example.badhibernate.dto.DepartmentDto;
import com.example.badhibernate.entity.Department;
import com.example.badhibernate.repository.DepartmentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class NPlusOneService {

    private final DepartmentRepository departmentRepository;

    public NPlusOneService(DepartmentRepository departmentRepository) {
        this.departmentRepository = departmentRepository;
    }

    /**
     * ANTIPATTERN 1: N+1 Queries Problem.
     * Fetches N departments (1 SELECT query), then loops through each department
     * and triggers lazy loading for employees (N extra SELECT queries).
     * Total SQL queries generated: 1 + N.
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsSubOptimal() {
        List<Department> departments = departmentRepository.findAllWithEmployeesOptimal(); // 1 Query

        return departments.stream()
                .map(d -> new DepartmentDto(
                        d.getId(),
                        d.getName(),
                        d.getLocation(),
                        d.getEmployees().size() // Triggers 1 SELECT query per department!
                ))
                .toList();
    }

    /**
     * OPTIMAL FIX: Uses JOIN FETCH in JPQL to load departments and employees in a single SELECT.
     * Total SQL queries generated: 1.
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsOptimal() {
        List<Department> departments = departmentRepository.findAllWithEmployeesOptimal();

        return departments.stream()
                .map(d -> new DepartmentDto(
                        d.getId(),
                        d.getName(),
                        d.getLocation(),
                        d.getEmployees().size()
                ))
                .toList();
    }
}