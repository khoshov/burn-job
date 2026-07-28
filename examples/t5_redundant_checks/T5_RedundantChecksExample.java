package examples.t5_redundant_checks;

import java.util.List;

/**
 * 🚨 T5. Избыточные проверки и блоки кода (Redundant Checks & Filters)
 * Пример: выполнение фильтрации в памяти Java после запроса всей таблицы из БД.
 */
public class T5_RedundantChecksExample {

    public record Order(Long id, String status) {}

    // ❌ Sub-optimal: Ручная фильтрация в Stream API после выборки findAll()
    public List<Order> filterInJavaSubOptimal(List<Order> allOrdersFromDb, String targetStatus) {
        return allOrdersFromDb.stream()
                .filter(o -> targetStatus.equals(o.status())) // Лишняя фильтрация в RAM
                .toList();
    }

    // ✅ Optimal Fix (Вариант 5.2): Делегация бизнес-условия в SQL WHERE
    // SELECT o FROM Order o WHERE o.status = :targetStatus
}
