package com.example.badhibernate.service;

import com.example.badhibernate.dto.EmployeeSimpleDto;
import com.example.badhibernate.entity.Employee;
import com.example.badhibernate.repository.EmployeeRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class FullEntityFetchService {

    private final EmployeeRepository employeeRepository;

    public FullEntityFetchService(EmployeeRepository employeeRepository) {
        this.employeeRepository = employeeRepository;
    }

    /**
     * OPTIMAL FIX: Uses Spring Data JPA interface projection.
     * Generates `SELECT id, first_name, last_name, email FROM employees`, skipping heavy columns and entity overhead.
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesSubOptimal() {
        return employeeRepository.findAllProjectedBy().stream()
                .map(p -> new EmployeeSimpleDto(p.getId(), p.getFirstName(), p.getLastName(), p.getEmail()))
                .toList();
    }

    /**
     * OPTIMAL FIX: Uses Spring Data JPA interface projection.
     * Generates `SELECT id, first_name, last_name, email FROM employees`, skipping heavy columns and entity overhead.
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesOptimal() {
        return employeeRepository.findAllProjectedBy().stream()
                .map(p -> new EmployeeSimpleDto(p.getId(), p.getFirstName(), p.getLastName(), p.getEmail()))
                .toList();
    }
}