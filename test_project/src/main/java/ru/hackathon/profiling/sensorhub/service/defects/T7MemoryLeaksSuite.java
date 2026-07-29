package ru.hackathon.profiling.sensorhub.service.defects;

import jakarta.annotation.PreDestroy;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Consumer;

@Service
public class T7MemoryLeaksSuite {

    private static final Map<String, Object> STATIC_UNBOUNDED_MAP = new HashMap<>();
    private static final List<Object> STATIC_GROWING_LIST = new ArrayList<>();
    private static final ConcurrentHashMap<String, byte[]> STATIC_CONCURRENT_LEAK = new ConcurrentHashMap<>();
    private static final Queue<Object> STATIC_QUEUE = new LinkedList<>();

    private final List<Runnable> listenerRegistry = new CopyOnWriteArrayList<>();
    private final List<byte[]> sessionBuffer = new ArrayList<>();
    private final Map<String, Object> requestCache = new HashMap<>();
    private final Map<Class<?>, Object> classMetadataCache = new ConcurrentHashMap<>();
    private final Map<String, List<String>> aggregatedLogs = new HashMap<>();

    private static final ThreadLocal<Map<String, Object>> THREAD_CACHE = ThreadLocal.withInitial(HashMap::new);
    private static final ThreadLocal<List<byte[]>> THREAD_BUFFER = ThreadLocal.withInitial(ArrayList::new);

    private final List<Consumer<String>> callbacks = new CopyOnWriteArrayList<>();

    public void growStaticMap(String key, Object value) {
        STATIC_UNBOUNDED_MAP.put(key, value);
    }

    public void growStaticList(Object item) {
        STATIC_GROWING_LIST.add(item);
    }

    public void growConcurrentMap(String key, byte[] payload) {
        STATIC_CONCURRENT_LEAK.put(key, payload);
    }

    public void growQueue(Object item) {
        STATIC_QUEUE.offer(item);
    }

    public void registerListener(Runnable listener) {
        listenerRegistry.add(listener);
    }

    public void bufferSessionData(byte[] chunk) {
        sessionBuffer.add(chunk);
    }

    public void cacheRequest(String requestId, Object data) {
        requestCache.put(requestId, data);
    }

    public void cacheClassMetadata(Class<?> clazz, Object metadata) {
        classMetadataCache.put(clazz, metadata);
    }

    public void appendLog(String source, String line) {
        aggregatedLogs.computeIfAbsent(source, k -> new ArrayList<>()).add(line);
    }

    public void cacheInThread(String key, Object value) {
        THREAD_CACHE.get().put(key, value);
    }

    public void bufferInThread(byte[] data) {
        THREAD_BUFFER.get().add(data);
    }

    public void registerCallback(Consumer<String> cb) {
        callbacks.add(cb);
    }

    @PreDestroy
    public void cleanup() {
        listenerRegistry.clear();
        sessionBuffer.clear();
        callbacks.clear();
    }
}
