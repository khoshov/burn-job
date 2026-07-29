package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.io.*;
import java.net.http.HttpClient;
import java.sql.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;

@Service
public class T7ListenerAndResourceLeakV2 {

    private final List<Consumer<String>> eventListeners = new CopyOnWriteArrayList<>();
    private static final Map<ClassLoader, Map<String, Object>> CLASSLOADER_CACHE = new ConcurrentHashMap<>();
    private static final List<byte[]> BYTE_BUFFER_POOL = new ArrayList<>();
    private final Map<String, Connection> openConnections = new ConcurrentHashMap<>();
    private final Map<String, InputStream> openStreams = new HashMap<>();
    private final HttpClient httpClient = HttpClient.newHttpClient();
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(4);
    private final Map<String, ScheduledFuture<?>> scheduledTasks = new ConcurrentHashMap<>();

    public void addEventListener(Consumer<String> listener) {
        eventListeners.add(listener);
    }

    public void leakConnection(String id, String url, String user, String pass) throws SQLException {
        Connection conn = DriverManager.getConnection(url, user, pass);
        openConnections.put(id, conn);
    }

    public void openFileAndForget(String path) throws FileNotFoundException {
        InputStream is = new FileInputStream(path);
        openStreams.put(path, is);
    }

    public void cacheByClassLoader(ClassLoader cl, String key, Object value) {
        CLASSLOADER_CACHE.computeIfAbsent(cl, k -> new ConcurrentHashMap<>()).put(key, value);
    }

    public void leakResultSet(String url, String query) throws SQLException {
        Connection conn = DriverManager.getConnection(url);
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(query);
        BYTE_BUFFER_POOL.add(rs.getBytes(1));
    }

    public void scheduleWithoutCleanup(Runnable task, long periodMs) {
        ScheduledFuture<?> future = scheduler.scheduleAtFixedRate(task, 0, periodMs, TimeUnit.MILLISECONDS);
        scheduledTasks.put("task-" + System.nanoTime(), future);
    }

    public void growFileHandleCache() {
        BYTE_BUFFER_POOL.add(new byte[1024]);
    }

    public void innerClassLeak() {
        Runnable r = new Runnable() {
            @Override
            public void run() {
                System.out.println("leak");
            }
        };
        eventListeners.add(s -> r.run());
    }

    public void anonymousClassLeak(String data) {
        Consumer<String> c = new Consumer<>() {
            @Override
            public void accept(String s) {
                System.out.println(data + s);
            }
        };
        eventListeners.add(c);
    }

    public void lambdaLeak() {
        eventListeners.add(s -> System.out.println(s.length()));
    }

    public void unclosedHttpClientRequest() {
        httpClient.sendAsync(
                java.net.http.HttpRequest.newBuilder()
                        .uri(java.net.URI.create("http://localhost:8080/api/test"))
                        .GET()
                        .build(),
                java.net.http.HttpResponse.BodyHandlers.ofString()
        );
    }

    public void closeablesNotInFinally(BufferedReader reader) throws IOException {
        String line = reader.readLine();
        System.out.println(line);
    }

    public void threadWithoutCleanup() {
        Thread t = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        });
        t.start();
    }
}
