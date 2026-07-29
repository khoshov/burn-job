package ru.hackathon.profiling.sensorhub.service.defects.notdefect;

import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class NotDefectBoundedCache {

    private static final int MAX_STATION_CACHE = 10_000;
    private static final int MAX_RECENT_QUERIES = 500;

    private final Map<String, Object> stationCache = new LinkedHashMap<>() {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, Object> eldest) {
            return size() > MAX_STATION_CACHE;
        }
    };

    private final Map<String, byte[]> recentQueryCache = new ConcurrentHashMap<>() {
        @Override
        public byte[] put(String key, byte[] value) {
            if (size() >= MAX_RECENT_QUERIES) {
                clear();
            }
            return super.put(key, value);
        }
    };

    private final Map<Long, Object> measurementBuffer = new LinkedHashMap<>() {
        @Override
        protected boolean removeEldestEntry(Map.Entry<Long, Object> eldest) {
            return size() > 100;
        }
    };

    private final Map<String, String> lruCache = new LinkedHashMap<>(16, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
            return size() > 1000;
        }
    };

    public Object getFromStationCache(String key) {
        return stationCache.get(key);
    }

    public void putStationCache(String key, Object value) {
        stationCache.put(key, value);
    }

    public void cacheQuery(String queryId, byte[] result) {
        recentQueryCache.put(queryId, result);
    }

    public byte[] getCachedQuery(String queryId) {
        return recentQueryCache.get(queryId);
    }

    public void bufferMeasurement(Long stationId, Object data) {
        measurementBuffer.put(stationId, data);
    }

    public Object flushMeasurement(Long stationId) {
        return measurementBuffer.remove(stationId);
    }

    public String getLru(String key) {
        return lruCache.get(key);
    }

    public void putLru(String key, String value) {
        lruCache.put(key, value);
    }
}
