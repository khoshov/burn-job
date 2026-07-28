package examples.non_defects;

import java.util.List;

/**
 * 🟢 Section 7 Rule 2 (ND-2): Квадратичная сложность при ограниченном контрактом входе (N <= 8)
 * 
 * Обоснование:
 * Если размер коллекции строго ограничен API-контрактом (N <= 8 элементов, например, список статусов или вариантов),
 * вложенный цикл со сложностью O(N^2) выполняется за доли микросекунды и не вызывает деградацию производительности.
 */
public class ND2_BoundedQuadraticNonDefectExample {

    // Ограниченный список небольшого размера (N <= 8)
    private static final List<String> BOUNDED_STATUSES = List.of("SHIPPED", "DELIVERED", "PENDING", "CANCELLED");

    public boolean isStatusSupportedNonDefect(String targetStatus) {
        // Вложенный цикл по 4 элементам занимает наносекунды — НЕ является дефектом
        for (String status : BOUNDED_STATUSES) {
            if (status.equalsIgnoreCase(targetStatus)) {
                return true;
            }
        }
        return false;
    }
}
