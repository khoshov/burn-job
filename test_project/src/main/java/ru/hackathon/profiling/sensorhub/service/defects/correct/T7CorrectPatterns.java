package ru.hackathon.profiling.sensorhub.service.defects.correct;

import org.springframework.stereotype.Service;

import java.io.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.*;

@Service
public class T7CorrectPatterns {

    private static final Map<String, Object> BOUNDED_CACHE = new ConcurrentHashMap<>();
    private static final int MAX_CACHE_SIZE = 10_000;
    private static final Queue<Object> BOUNDED_QUEUE = new ArrayBlockingQueue<>(1000);

    private final List<Runnable> listenerRegistry = new CopyOnWriteArrayList<>();
    private final Map<String, Object> requestCache = new ConcurrentHashMap<>();

    private static final ThreadLocal<Map<String, Object>> THREAD_CACHE = ThreadLocal.withInitial(HashMap::new);

    public void safePutCache(String key, Object value) {
        if (BOUNDED_CACHE.size() >= MAX_CACHE_SIZE) {
            String oldest = BOUNDED_CACHE.keySet().iterator().next();
            BOUNDED_CACHE.remove(oldest);
        }
        BOUNDED_CACHE.put(key, value);
    }

    public void safeAddToQueue(Object item) {
        if (!BOUNDED_QUEUE.offer(item)) {
            BOUNDED_QUEUE.poll();
            BOUNDED_QUEUE.offer(item);
        }
    }

    public void registerListener(Runnable listener) {
        listenerRegistry.add(listener);
    }

    public void removeListener(Runnable listener) {
        listenerRegistry.remove(listener);
    }

    public void safeCacheRequest(String requestId, Object data) {
        requestCache.put(requestId, data);
    }

    public void cleanupRequest(String requestId) {
        requestCache.remove(requestId);
    }

    public void cacheInThread(String key, Object value) {
        Map<String, Object> map = THREAD_CACHE.get();
        if (map.size() > 100) map.clear();
        map.put(key, value);
    }

    public void removeThreadCache() {
        THREAD_CACHE.remove();
    }

    public void safeFileRead(String path) throws IOException {
        try (InputStream is = new FileInputStream(path)) {
            is.readAllBytes();
        }
    }

    public void safeConnectionUse(String url) throws SQLException {
        try (Connection conn = DriverManager.getConnection(url);
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT 1")) {
            while (rs.next()) {
                System.out.println(rs.getInt(1));
            }
        }
    }

    public void safeSchedule(Runnable task, long periodMs) {
        ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
        scheduler.scheduleAtFixedRate(task, 0, periodMs, TimeUnit.MILLISECONDS);
        Runtime.getRuntime().addShutdownHook(new Thread(scheduler::shutdown));
    }

    public void safeLambdaConsumer(String data) {
        Consumer<String> c = s -> System.out.println(s.length());
        c.accept(data);
    }

    private interface Consumer<T> {
        void accept(T t);
    }
}
