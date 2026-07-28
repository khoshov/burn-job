package com.example.badhibernate.repository;

import com.example.badhibernate.dto.EmployeeSimpleDto;
import com.example.badhibernate.entity.Employee;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface EmployeeRepository extends JpaRepository<Employee, Long> {

    // Variant 1: Projection interface for optimal retrieval
    interface EmployeeSimpleProjection {
        Long getId();
        String getFirstName();
        String getLastName();
        String getEmail();
    }

    @Query("SELECT e.id as id, e.firstName as firstName, e.lastName as lastName, e.email as email FROM Employee e")
    List<EmployeeSimpleProjection> findAllProjectedBy();

    // Variant 2: JPQL Constructor Expression DTO Projection
    @Query("SELECT new com.example.badhibernate.dto.EmployeeSimpleDto(e.id, e.firstName, e.lastName, e.email) FROM Employee e")
    List<EmployeeSimpleDto> findSimpleDtosDirect();
}

