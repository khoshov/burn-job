package examples.non_defects;

import java.util.ArrayList;
import java.util.List;

/**
 * 🟢 Section 7 Rule 4 (ND-4): Промежуточная коллекция, ограниченная параметром запроса
 * 
 * Обоснование:
 * Коллекции в памяти, максимальный размер которых принудительно валидируется и ограничивается
 * параметрами входного HTTP-запроса (например, pageSize <= 50), имеют строго фиксированный
 * верхний предел памяти в рамках запроса и НЕ являются дефектом Memory Bloat.
 */
public class ND4_BoundedRequestCollectionNonDefectExample {

    public List<String> processBoundedPageRequest(int requestedPageSize) {
        // Жесткое ограничение максимального размера порции (не более 20 элементов)
        int safeSize = Math.min(Math.max(1, requestedPageSize), 20);

        List<String> pageItems = new ArrayList<>(safeSize);
        for (int i = 0; i < safeSize; i++) {
            pageItems.add("Item_" + i);
        }
        return pageItems;
    }
}
