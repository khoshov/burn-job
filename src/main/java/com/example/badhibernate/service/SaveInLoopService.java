package com.example.badhibernate.service;

import com.example.badhibernate.entity.Employee;
import com.example.badhibernate.repository.EmployeeRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.hibernate.SessionFactory;
import org.hibernate.StatelessSession;
import org.hibernate.Transaction;
import org.springframework.jdbc.core.BatchPreparedStatementSetter;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

@Service
public class SaveInLoopService {

    private final EmployeeRepository employeeRepository;
    private final JdbcTemplate jdbcTemplate;

    @PersistenceContext
    private EntityManager entityManager;

    public SaveInLoopService(EmployeeRepository employeeRepository, JdbcTemplate jdbcTemplate) {
        this.employeeRepository = employeeRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * ANTIPATTERN (SubOptimal): Saves entities one by one in a loop without JDBC batching.
     */
    @Transactional
    public long createEmployeesSubOptimal(int count) {
        long startTime = System.currentTimeMillis();

        for (int i = 0; i < count; i++) {
            employeeRepository.save(new Employee(
                    "SubOptFirst" + i,
                    "SubOptLast" + i,
                    "subopt" + System.nanoTime() + i + "@example.com",
                    BigDecimal.valueOf(50000 + i),
                    "Heavy biography text content for testing payload size " + i,
                    null
            ));
        }

        return System.currentTimeMillis() - startTime;
    }

    /**
     * FIX VARIANT 3.1 / 6.4: saveAll() with JDBC Batching
     */
    @Transactional
    public long createEmployeesVariant1_SaveAll(int count) {
        long startTime = System.currentTimeMillis();

        List<Employee> employees = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            employees.add(new Employee(
                    "OptFirst" + i,
                    "OptLast" + i,
                    "opt" + System.nanoTime() + i + "@example.com",
                    BigDecimal.valueOf(50000 + i),
                    "Heavy biography text content for testing payload size " + i,
                    null
            ));
        }

        employeeRepository.saveAll(employees);

        return System.currentTimeMillis() - startTime;
    }

    /**
     * FIX VARIANT 3.2 / 6.4: Spring JdbcTemplate batchUpdate
     */
    @Transactional
    public long createEmployeesVariant2_JdbcTemplate(int count) {
        long startTime = System.currentTimeMillis();

        String sql = "INSERT INTO employees (first_name, last_name, email, salary, detailed_biography) VALUES (?, ?, ?, ?, ?)";
        
        jdbcTemplate.batchUpdate(sql, new BatchPreparedStatementSetter() {
            @Override
            public void setValues(PreparedStatement ps, int i) throws SQLException {
                ps.setString(1, "JdbcFirst" + i);
                ps.setString(2, "JdbcLast" + i);
                ps.setString(3, "jdbc" + System.nanoTime() + i + "@example.com");
                ps.setBigDecimal(4, BigDecimal.valueOf(50000 + i));
                ps.setString(5, "Heavy biography text content for testing payload size " + i);
            }

            @Override
            public int getBatchSize() {
                return count;
            }
        });

        return System.currentTimeMillis() - startTime;
    }

    /**
     * FIX VARIANT 3.3 / 7.3: Hibernate StatelessSession Batch Insert
     */
    @Transactional
    public long createEmployeesVariant3_StatelessSession(int count) {
        long startTime = System.currentTimeMillis();

        SessionFactory sessionFactory = entityManager.getEntityManagerFactory().unwrap(SessionFactory.class);
        try (StatelessSession session = sessionFactory.openStatelessSession()) {
            Transaction tx = session.beginTransaction();
            for (int i = 0; i < count; i++) {
                session.insert(new Employee(
                        "StatelessFirst" + i,
                        "StatelessLast" + i,
                        "stateless" + System.nanoTime() + i + "@example.com",
                        BigDecimal.valueOf(50000 + i),
                        "Heavy biography text content for testing payload size " + i,
                        null
                ));
            }
            tx.commit();
        }

        return System.currentTimeMillis() - startTime;
    }

    /**
     * OPTIMAL FIX: Saves all items in a single collection call (saveAll()).
     */
    @Transactional
    public long createEmployeesOptimal(int count) {
        return createEmployeesVariant1_SaveAll(count);
    }

    /**
     * Feature Toggle Router for Save In Loop Fix Variants.
     */
    @Transactional
    public long createEmployeesByVariant(int count, String variant) {
        if (variant == null) variant = "v1";
        return switch (variant.toLowerCase()) {
            case "v1", "saveall" -> createEmployeesVariant1_SaveAll(count);
            case "v2", "jdbctemplate" -> createEmployeesVariant2_JdbcTemplate(count);
            case "v3", "stateless" -> createEmployeesVariant3_StatelessSession(count);
            case "suboptimal", "bad" -> createEmployeesSubOptimal(count);
            default -> createEmployeesOptimal(count);
        };
    }
}