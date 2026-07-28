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
     * ANTIPATTERN (SubOptimal): N+1 Queries Problem.
     * Total SQL queries generated: 1 + N.
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsSubOptimal() {
        List<Department> departments = departmentRepository.findAll(); // 1 Query

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
     * FIX VARIANT 1.1: JPQL JOIN FETCH
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsVariant1_JoinFetch() {
        List<Department> departments = departmentRepository.findAllWithEmployeesOptimal();
        return departments.stream()
                .map(d -> new DepartmentDto(d.getId(), d.getName(), d.getLocation(), d.getEmployees().size()))
                .toList();
    }

    /**
     * FIX VARIANT 1.2: EntityGraph Annotation
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsVariant2_EntityGraph() {
        List<Department> departments = departmentRepository.findAllWithEntityGraph();
        return departments.stream()
                .map(d -> new DepartmentDto(d.getId(), d.getName(), d.getLocation(), d.getEmployees().size()))
                .toList();
    }

    /**
     * FIX VARIANT 1.4: DTO Constructor Expression Direct Query
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsVariant3_DtoGroupBy() {
        return departmentRepository.findDepartmentDtosDirect();
    }

    /**
     * OPTIMAL FIX: Uses default optimal implementation (Variant 1.1).
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsOptimal() {
        return getDepartmentsVariant1_JoinFetch();
    }

    /**
     * Feature Toggle Router for N+1 Query Fix Variants.
     */
    @Transactional(readOnly = true)
    public List<DepartmentDto> getDepartmentsByVariant(String variant) {
        if (variant == null) variant = "v1";
        return switch (variant.toLowerCase()) {
            case "v1", "join_fetch" -> getDepartmentsVariant1_JoinFetch();
            case "v2", "entity_graph" -> getDepartmentsVariant2_EntityGraph();
            case "v3", "v4", "dto_groupby" -> getDepartmentsVariant3_DtoGroupBy();
            case "suboptimal", "bad" -> getDepartmentsSubOptimal();
            default -> getDepartmentsOptimal();
        };
    }
}