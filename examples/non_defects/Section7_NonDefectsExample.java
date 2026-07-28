package examples.non_defects;

import java.util.*;

/**
 * 🟢 Section 7 Rules — Исключения из дефектов (Non-Defects)
 * Примеры кода и структур, которые СОЗНАТЕЛЬНО НЕ являются дефектами производительности.
 */
public class Section7_NonDefectsExample {

    // 🟢 Rule 1: Field Ordering (HotSpot JVM самостоятельно выравнивает поля в RAM)
    public static class FieldOrderingNonDefect {
        byte b1;
        long l1;
        byte b2;
        long l2;
        // JOL подтверждает: размер объекта равен 40 байтам независимо от порядка в коде.
    }

    // 🟢 Rule 2: Small Quadratic Loops (N <= 8)
    public boolean matchSmallStatusListNonDefect(List<String> small8Items, String target) {
        // Вложенный цикл по 5 элементов выполняется за наносекунды и НЕ является дефектом
        for (String item : small8Items) {
            if (item.equals(target)) return true;
        }
        return false;
    }

    // 🟢 Rule 3: Bounded LRU Reference Caches
    public static class BoundedCacheNonDefect {
        private final int maxSize = 50;
        private final Map<String, String> lruCache = Collections.synchronizedMap(new LinkedHashMap<String, String>(maxSize, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
                return size() > maxSize; // Рост ограничен 50 элементами — НЕ утечка памяти
            }
        });
    }

    // 🟢 Rule 4: Request Contract Bounded Collections
    public List<String> getBoundedPageCollectionNonDefect(int pageSize) {
        int boundedSize = Math.min(pageSize, 10);
        return new ArrayList<>(boundedSize);
    }
}
