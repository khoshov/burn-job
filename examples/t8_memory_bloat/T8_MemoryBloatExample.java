package examples.t8_memory_bloat;

import java.util.List;

/**
 * 🚨 T8. Перерасход памяти (Memory Bloat & RAM Pagination)
 * Пример: выгрузка таблицы из 1 000 000 строк в Heap ради получения первой страницы.
 */
public class T8_MemoryBloatExample {

    // ❌ Sub-optimal: Считывание всех строк таблицы и пагинация skip/limit в памяти
    public List<String> pageInMemorySubOptimal(List<String> allMillionRows, int page, int size) {
        return allMillionRows.stream()
                .skip((long) page * size)
                .limit(size)
                .toList(); // Риск OutOfMemoryError
    }

    // ✅ Optimal Fix (Вариант 8.1): Перенос LIMIT / OFFSET на уровень СУБД через Spring Data Pageable
    // SELECT o FROM Order o WHERE o.status = :status LIMIT :size OFFSET :offset
}
