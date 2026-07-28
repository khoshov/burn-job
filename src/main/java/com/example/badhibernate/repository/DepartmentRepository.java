package com.example.badhibernate.repository;

import com.example.badhibernate.dto.DepartmentDto;
import com.example.badhibernate.entity.Department;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface DepartmentRepository extends JpaRepository<Department, Long> {

    // Variant 1: JOIN FETCH JPQL Query
    @Query("SELECT DISTINCT d FROM Department d LEFT JOIN FETCH d.employees")
    List<Department> findAllWithEmployeesOptimal();

    // Variant 2: EntityGraph annotation
    @EntityGraph(attributePaths = {"employees"})
    @Query("SELECT d FROM Department d")
    List<Department> findAllWithEntityGraph();

    // Variant 4: DTO Constructor Expression Query
    @Query("SELECT new com.example.badhibernate.dto.DepartmentDto(d.id, d.name, d.location, SIZE(d.employees)) FROM Department d")
    List<DepartmentDto> findDepartmentDtosDirect();
}

