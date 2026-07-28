package com.example.badhibernate.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Table(name = "employees")
public class Employee {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String firstName;
    private String lastName;
    private String email;
    private BigDecimal salary;

    // ANTIPATTERN: Large field fetched eagerly with full entity when mapping simple DTO
    @Column(columnDefinition = "TEXT")
    private String detailedBiography;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "department_id")
    private Department department;

    public Employee() {}

    public Employee(String firstName, String lastName, String email, BigDecimal salary, String detailedBiography, Department department) {
        this.firstName = firstName;
        this.lastName = lastName;
        this.email = email;
        this.salary = salary;
        this.detailedBiography = detailedBiography;
        this.department = department;
    }

    public Long getId() { return id; }
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public BigDecimal getSalary() { return salary; }
    public void setSalary(BigDecimal salary) { this.salary = salary; }
    public String getDetailedBiography() { return detailedBiography; }
    public void setDetailedBiography(String detailedBiography) { this.detailedBiography = detailedBiography; }
    public Department getDepartment() { return department; }
    public void setDepartment(Department department) { this.department = department; }
}
