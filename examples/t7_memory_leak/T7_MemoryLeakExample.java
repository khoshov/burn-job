package examples.t7_memory_leak;

import jakarta.persistence.EntityManager;
import java.util.List;

/**
 * 🚨 T7. Утечка памяти (Memory Leaks)
 * Пример: переполнение Hibernate PersistenceContext (1st level cache) при массовой обработке 100 000+ сущностей.
 */
public class T7_MemoryLeakExample {

    // ❌ Sub-optimal: Сохранение объектов в сессии без flush/clear (накопление в 1st level cache)
    public void processBulkSubOptimal(List<Object> entities, EntityManager em) {
        for (Object entity : entities) {
            em.persist(entity); // Объект навечно остается в памяти сессии
        }
    }

    // ✅ Optimal Fix (Вариант 7.1): Периодическая очистка PersistenceContext
    public void processBulkOptimal(List<Object> entities, EntityManager em) {
        for (int i = 0; i < entities.size(); i++) {
            em.persist(entities.get(i));
            if (i > 0 && i % 50 == 0) {
                em.flush();
                em.clear(); // Сброс ссылок для работы Garbage Collector
            }
        }
    }
}
