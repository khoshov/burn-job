package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T6]
 * Bottleneck: N+1 query problem with lazy collection initialization
 * Original file (T6_DbQueriesExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T6_DbQueriesExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t6_db_queries;

import java.util.List;

/**
 * 🚀 Fix 1: Batch Fetching using Hibernate @BatchSize
 * Reduces N+1 to N/BatchSize+1 queries without changing query structure
 */
public class T6_DbQueriesExample_BatchSize {

    public static class Department {
        private Long id;
        private String name;
        @org.hibernate.annotations.BatchSize(size = 20)
        private List<String> employees; // LAZY collection with batch fetching
        
        public List<String> getEmployees() { return employees; }
    }

    // ✅ Optimal: Batch fetching reduces queries from N+1 to ceil(N/20)+1
    public int countAllEmployeesBatchSize(List<Department> departments) {
        int count = 0;
        for (Department d : departments) {
            count += d.getEmployees().size(); // Batch initialized in groups of 20
        }
        return count;
    }
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t6_db_queries;

import javax.persistence.*;
import java.util.List;

/**
 * 🚀 Fix 2: Entity Graph (JPA 2.1) for dynamic fetch strategy
 * Allows per-query control over lazy loading without changing entity mapping
 */
public class T6_DbQueriesExample_EntityGraph {

    @Entity
    @NamedEntityGraph(name = "Department.employees", 
                      attributeNodes = @NamedAttributeNode("employees"))
    public static class Department {
        @Id
        private Long id;
        private String name;
        
        @OneToMany(fetch = FetchType.LAZY)
        @JoinColumn(name = "department_id")
        private List<String> employees;
        
        public List<String> getEmployees() { return employees; }
    }

    // ✅ Optimal: Single query with entity graph
    public int countAllEmployeesEntityGraph(EntityManager em) {
        EntityGraph<?> graph = em.getEntityGraph("Department.employees");
        
        TypedQuery<Department> query = em.createQuery(
            "SELECT d FROM Department d", Department.class);
        query.setHint("javax.persistence.fetchgraph", graph);
        
        List<Department> departments = query.getResultList();
        
        int count = 0;
        for (Department d : departments) {
            count += d.getEmployees().size(); // Already loaded in single query
        }
        return count;
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t6_db_queries;

import javax.persistence.*;
import java.util.List;

/**
 * 🚀 Fix 3: DTO Projection with subquery
 * Avoids loading collections entirely by computing aggregate in database
 */
public class T6_DbQueriesExample_DTO {

    // DTO class for projection
    public static class DepartmentEmployeeCount {
        private Long departmentId;
        private String departmentName;
        private Long employeeCount;
        
        public DepartmentEmployeeCount(Long departmentId, String departmentName, Long employeeCount) {
            this.departmentId = departmentId;
            this.departmentName = departmentName;
            this.employeeCount = employeeCount;
        }
        
        public Long getEmployeeCount() { return employeeCount; }
    }

    // ✅ Optimal: Single query with subquery for count
    public int countAllEmployeesDTO(EntityManager em) {
        TypedQuery<DepartmentEmployeeCount> query = em.createQuery(
            "SELECT NEW examples.t6_db_queries.T6_DbQueriesExample_DTO$DepartmentEmployeeCount(" +
            "  d.id, d.name, " +
            "  (SELECT COUNT(e) FROM Employee e WHERE e.department.id = d.id)" +
            ") FROM Department d", 
            DepartmentEmployeeCount.class);
        
        List<DepartmentEmployeeCount> results = query.getResultList();
        
        return results.stream()
            .mapToLong(DepartmentEmployeeCount::getEmployeeCount)
            .sum();
    }
}
    */

}
