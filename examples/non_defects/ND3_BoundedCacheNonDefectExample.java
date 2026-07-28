package examples.non_defects;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 🟢 Section 7 Rule 3 (ND-3): Кэш с заданной границей и политикой вытеснения (Bounded Cache)
 * 
 * Обоснование:
 * Накопление элементов в кэше до сконфигурированного максимального размера (maxSize) является
 * штатным проектным поведением. При превышении размера автоматически срабатывает вытеснение (LRU/LFU),
 * поэтому неограниченного роста памяти не происходит, и это НЕ является утечкой памяти.
 */
public class ND3_BoundedCacheNonDefectExample {

    private final int maxSize = 100;
    
    // Синхронизированный LRU кэш с лимитом maxSize=100
    private final Map<String, String> boundedLruCache = Collections.synchronizedMap(
        new LinkedHashMap<String, String>(maxSize, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
                return size() > maxSize; // Автоматическое вытеснение старых элементов
            }
        }
    );

    public void putInCache(String key, String value) {
        boundedLruCache.put(key, value); // Безопасное хранение, ограничено 100 элементами
    }

    public String getFromCache(String key) {
        return boundedLruCache.get(key);
    }
}
