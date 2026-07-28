package com.example.badhibernate.service;

import com.example.badhibernate.dto.EmployeeSimpleDto;
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
     * OPTIMIZED VARIANT 1: Uses Spring Data JPA Interface Projection with explicit column selection.
     * Eliminates full entity fetch and heavy @Lob column loading.
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesSubOptimal() {
        return employeeRepository.findAllProjectedBy().stream()
                .map(p -> new EmployeeSimpleDto(p.getId(), p.getFirstName(), p.getLastName(), p.getEmail()))
                .toList();
    }

    /**
     * FIX VARIANT 3.1 / 4.1: Spring Data JPA Interface Projection
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesVariant1_InterfaceProjection() {
        return employeeRepository.findAllProjectedBy().stream()
                .map(p -> new EmployeeSimpleDto(p.getId(), p.getFirstName(), p.getLastName(), p.getEmail()))
                .toList();
    }

    /**
     * FIX VARIANT 3.1 / 4.3: JPQL Constructor Expression DTO Projection
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesVariant2_DtoConstructor() {
        return employeeRepository.findSimpleDtosDirect();
    }

    /**
     * OPTIMAL FIX: Uses default interface projection.
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesOptimal() {
        return getEmployeesVariant1_InterfaceProjection();
    }

    /**
     * Feature Toggle Router for Full Entity Fetch Fix Variants.
     */
    @Transactional(readOnly = true)
    public List<EmployeeSimpleDto> getEmployeesByVariant(String variant) {
        if (variant == null) variant = "v1";
        return switch (variant.toLowerCase()) {
            case "v1", "projection" -> getEmployeesVariant1_InterfaceProjection();
            case "v2", "constructor" -> getEmployeesVariant2_DtoConstructor();
            case "suboptimal", "bad" -> getEmployeesSubOptimal();
            default -> getEmployeesOptimal();
        };
    }
}