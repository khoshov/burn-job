package com.example.badhibernate.repository;

import com.example.badhibernate.entity.Department;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface DepartmentRepository extends JpaRepository<Department, Long> {

    // Optimal fix method provided for comparison
    @Query("SELECT DISTINCT d FROM Department d LEFT JOIN FETCH d.employees")
    List<Department> findAllWithEmployeesOptimal();
}
