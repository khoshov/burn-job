package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T4]
 * Bottleneck: Unaligned field layout and heavy LOB column fetch
 * Original file (T4_DataLayoutExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T4_DataLayoutExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t4_data_layout;

import javax.persistence.*;
import java.util.List;

/**
 * ✅ T4 Fix - Variant 1: Projection Pattern with JPA Constructor Expression
 * Fetches only lightweight fields via JPQL constructor expression.
 * Heavy LOB columns are never loaded in this query path.
 */
public class T4_DataLayoutExample_V1 {

    // Entity with all fields (for write operations)
    @Entity
    @Table(name = "employees")
    public static class EmployeeFullEntity {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        private Long id;
        
        @Column(name = "name")
        private String name;
        
        @Lob
        @Column(name = "photo", columnDefinition = "BLOB")
        private byte[] heavyPhotoLob;
        
        @Lob
        @Column(name = "biography", columnDefinition = "CLOB")
        private String detailedBiography;
        
        // Getters and setters omitted for brevity
    }

    // Lightweight DTO for read operations
    public record EmployeeLightweightDto(Long id, String name) {}

    // Repository with projection query
    @Repository
    public static class EmployeeRepository {
        @PersistenceContext
        private EntityManager entityManager;

        public List<EmployeeLightweightDto> findAllLightweight() {
            String jpql = "SELECT new examples.t4_data_layout.T4_DataLayoutExample_V1$EmployeeLightweightDto(e.id, e.name) " +
                         "FROM EmployeeFullEntity e";
            return entityManager.createQuery(jpql, EmployeeLightweightDto.class)
                               .getResultList();
        }

        // Separate method for full entity when needed (e.g., update)
        public EmployeeFullEntity findFullEntityById(Long id) {
            return entityManager.find(EmployeeFullEntity.class, id);
        }
    }
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t4_data_layout;

import javax.persistence.*;

/**
 * ✅ T4 Fix - Variant 2: Vertical Sharding with Lazy Loading
 * Heavy LOB columns moved to separate table with LAZY fetch.
 * Base table queries never touch LOB data.
 */
public class T4_DataLayoutExample_V2 {

    // Base entity - lightweight, frequently queried
    @Entity
    @Table(name = "employee_base")
    public static class EmployeeBase {
        @Id
        @GeneratedValue(strategy = GenerationType.IDENTITY)
        private Long id;
        
        @Column(name = "name")
        private String name;
        
        @OneToOne(mappedBy = "employee", fetch = FetchType.LAZY, cascade = CascadeType.ALL)
        private EmployeeDetail detail;
        
        // Getters and setters
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public EmployeeDetail getDetail() { return detail; }
        public void setDetail(EmployeeDetail detail) { this.detail = detail; }
    }

    // Detail entity - heavy LOB columns, lazily loaded
    @Entity
    @Table(name = "employee_detail")
    public static class EmployeeDetail {
        @Id
        private Long id;
        
        @MapsId
        @OneToOne(fetch = FetchType.LAZY)
        @JoinColumn(name = "employee_id")
        private EmployeeBase employee;
        
        @Lob
        @Column(name = "photo", columnDefinition = "BLOB")
        private byte[] heavyPhotoLob;
        
        @Lob
        @Column(name = "biography", columnDefinition = "CLOB")
        private String detailedBiography;
        
        // Getters and setters
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public EmployeeBase getEmployee() { return employee; }
        public void setEmployee(EmployeeBase employee) { this.employee = employee; }
        public byte[] getHeavyPhotoLob() { return heavyPhotoLob; }
        public void setHeavyPhotoLob(byte[] heavyPhotoLob) { this.heavyPhotoLob = heavyPhotoLob; }
        public String getDetailedBiography() { return detailedBiography; }
        public void setDetailedBiography(String detailedBiography) { this.detailedBiography = detailedBiography; }
    }

    // Repository with explicit lazy loading control
    @Repository
    public static class EmployeeRepository {
        @PersistenceContext
        private EntityManager entityManager;

        public EmployeeBase findBaseById(Long id) {
            // Only loads base table - no LOB columns
            return entityManager.find(EmployeeBase.class, id);
        }

        public EmployeeDetail findDetailByEmployeeId(Long employeeId) {
            // Explicitly fetch detail when needed
            return entityManager.find(EmployeeDetail.class, employeeId);
        }
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t4_data_layout;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.stream.Stream;

/**
 * ✅ T4 Fix - Variant 3: Native Query with Column Selection and Streaming
 * Uses JDBC directly to select only lightweight columns.
 * Streaming avoids loading all results into memory.
 */
public class T4_DataLayoutExample_V3 {

    // Lightweight DTO
    public record EmployeeLightweightDto(Long id, String name) {}

    // Full entity (for write operations)
    public static class EmployeeFullEntity {
        private Long id;
        private String name;
        private byte[] heavyPhotoLob;
        private String detailedBiography;
        
        public EmployeeFullEntity() {}
        
        public EmployeeFullEntity(Long id, String name) {
            this.id = id;
            this.name = name;
        }
        
        // Getters and setters
        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public byte[] getHeavyPhotoLob() { return heavyPhotoLob; }
        public void setHeavyPhotoLob(byte[] heavyPhotoLob) { this.heavyPhotoLob = heavyPhotoLob; }
        public String getDetailedBiography() { return detailedBiography; }
        public void setDetailedBiography(String detailedBiography) { this.detailedBiography = detailedBiography; }
    }

    // Repository with native query and streaming
    @Repository
    public static class EmployeeRepository {
        private final JdbcTemplate jdbcTemplate;

        public EmployeeRepository(JdbcTemplate jdbcTemplate) {
            this.jdbcTemplate = jdbcTemplate;
        }

        @Transactional(readOnly = true)
        public Stream<EmployeeLightweightDto> streamAllLightweight() {
            String sql = "SELECT id, name FROM employees";
            return jdbcTemplate.queryForStream(sql, 
                (rs, rowNum) -> new EmployeeLightweightDto(rs.getLong("id"), rs.getString("name"))
            );
        }

        @Transactional(readOnly = true)
        public EmployeeFullEntity findFullEntityById(Long id) {
            String sql = "SELECT id, name, photo, biography FROM employees WHERE id = ?";
            return jdbcTemplate.queryForObject(sql, new Object[]{id}, (rs, rowNum) -> {
                EmployeeFullEntity entity = new EmployeeFullEntity();
                entity.setId(rs.getLong("id"));
                entity.setName(rs.getString("name"));
                entity.setHeavyPhotoLob(rs.getBytes("photo"));
                entity.setDetailedBiography(rs.getString("biography"));
                return entity;
            });
        }
    }

    // Usage example
    public static class EmployeeService {
        private final EmployeeRepository repository;

        public EmployeeService(EmployeeRepository repository) {
            this.repository = repository;
        }

        public void processAllEmployees() {
            // Stream processes one row at a time - no LOB columns loaded
            try (Stream<EmployeeLightweightDto> stream = repository.streamAllLightweight()) {
                stream.forEach(dto -> {
                    System.out.println("Processing employee: " + dto.id() + " - " + dto.name());
                    // No LOB data loaded, fast processing
                });
            }
        }
    }
}
    */

}
