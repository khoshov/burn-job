package com.example.badhibernate.config;

import com.example.badhibernate.entity.Department;
import com.example.badhibernate.entity.Employee;
import com.example.badhibernate.entity.Order;
import com.example.badhibernate.entity.OrderItem;
import com.example.badhibernate.repository.DepartmentRepository;
import com.example.badhibernate.repository.OrderRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Component
public class DataInitializer implements CommandLineRunner {

    private final DepartmentRepository departmentRepository;
    private final OrderRepository orderRepository;

    public DataInitializer(DepartmentRepository departmentRepository, OrderRepository orderRepository) {
        this.departmentRepository = departmentRepository;
        this.orderRepository = orderRepository;
    }

    @Override
    @Transactional
    public void run(String... args) {
        System.out.println(">>> SEEDING INITIAL DATABASE RECORDS FOR PERFORMANCE DEMONSTRATION <<<");

        // Seed 30 Departments, each with 15 Employees
        List<Department> departments = new ArrayList<>();
        for (int d = 1; d <= 30; d++) {
            Department dept = new Department("Department-" + d, "Building " + (d % 5 + 1));
            for (int e = 1; e <= 15; e++) {
                String bio = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. ".repeat(20);
                Employee emp = new Employee(
                        "FirstName" + d + "_" + e,
                        "LastName" + d + "_" + e,
                        "emp" + d + "_" + e + "@company.com",
                        BigDecimal.valueOf(40000 + (d * 100) + e),
                        bio,
                        dept
                );
                dept.getEmployees().add(emp);
            }
            departments.add(dept);
        }
        departmentRepository.saveAll(departments);

        // Seed 500 Orders with 3 items each
        List<Order> orders = new ArrayList<>();
        String[] statuses = {"NEW", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"};
        for (int o = 1; o <= 500; o++) {
            String status = statuses[o % statuses.length];
            Order order = new Order(
                    "ORD-" + (10000 + o),
                    "customer" + o + "@domain.com",
                    status,
                    LocalDateTime.now().minusDays(o % 30),
                    BigDecimal.valueOf(100 + (o * 5))
            );

            for (int i = 1; i <= 3; i++) {
                OrderItem item = new OrderItem(
                        "Product-" + (i * o),
                        i,
                        BigDecimal.valueOf(25.5 * i),
                        order
                );
                order.getItems().add(item);
            }
            orders.add(order);
        }
        orderRepository.saveAll(orders);

        System.out.println(">>> DATABASE SEEDED SUCCESSFULLY: 30 Departments, 450 Employees, 500 Orders <<<");
    }
}
