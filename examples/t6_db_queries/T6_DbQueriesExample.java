package examples.t6_db_queries;

import java.util.List;

/**
 * 🚨 T6. Ошибки в запросах к базе данных (Database Query Errors)
 * Пример: проблема N+1 SQL запросов при выгрузке ленивых коллекций.
 */
public class T6_DbQueriesExample {

    public static class Department {
        private Long id;
        private String name;
        private List<String> employees; // LAZY collection
        
        public List<String> getEmployees() { return employees; }
    }

    // ❌ Sub-optimal (N+1 queries): 1 SELECT for departments + N SELECTs for employees
    public int countAllEmployeesSubOptimal(List<Department> departments) {
        int count = 0;
        for (Department d : departments) {
            count += d.getEmployees().size(); // Инициализация ленивой коллекции на каждом шаге
        }
        return count;
    }

    // ✅ Optimal Fix (Вариант 6.1): JPQL JOIN FETCH
    // SELECT DISTINCT d FROM Department d LEFT JOIN FETCH d.employees (1 SQL запрос)
}
