package com.example.badhibernate.service;

import one.profiler.AsyncProfiler;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

@Service
public class ProfilerService {

    private AsyncProfiler asyncProfiler;
    private final Path latestFlamegraphPath = Paths.get(System.getProperty("java.io.tmpdir"), "latest_flamegraph.html");

    public ProfilerService() {
        try {
            this.asyncProfiler = AsyncProfiler.getInstance();
        } catch (Throwable t) {
            System.err.println("AsyncProfiler initialization warning: " + t.getMessage());
            this.asyncProfiler = null;
        }
    }

    public boolean isAvailable() {
        return asyncProfiler != null;
    }

    public synchronized String start(String event, Long intervalNs) {
        if (!isAvailable()) {
            throw new IllegalStateException("AsyncProfiler is not available on this environment.");
        }
        String evt = (event != null && !event.isBlank()) ? event : "cpu";
        long interval = (intervalNs != null && intervalNs > 0) ? intervalNs : 1_000_000L;

        String command = String.format("start,event=%s,interval=%d", evt, interval);
        try {
            return asyncProfiler.execute(command);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to start profiler: " + e.getMessage(), e);
        }
    }

    public synchronized String stopAndGenerateFlamegraph() {
        if (!isAvailable()) {
            throw new IllegalStateException("AsyncProfiler is not available.");
        }
        File targetFile = latestFlamegraphPath.toFile();
        String command = String.format("stop,file=%s,flamegraph", targetFile.getAbsolutePath());
        try {
            return asyncProfiler.execute(command);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to stop profiler: " + e.getMessage(), e);
        }
    }

    public synchronized String getStatus() {
        if (!isAvailable()) {
            return "AsyncProfiler unavailable";
        }
        try {
            return asyncProfiler.execute("status");
        } catch (IOException e) {
            return "Error retrieving status: " + e.getMessage();
        }
    }

    public synchronized String getLatestFlamegraphHtml() throws IOException {
        if (Files.exists(latestFlamegraphPath)) {
            return Files.readString(latestFlamegraphPath);
        }
        return "<!DOCTYPE html><html><body><h2>No flamegraph recorded yet.</h2><p>Start and stop the profiler to generate one.</p></body></html>";
    }

    public Map<String, Object> profileForDuration(int seconds, String event) {
        start(event, 1_000_000L);
        try {
            Thread.sleep(seconds * 1000L);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        String stopMessage = stopAndGenerateFlamegraph();

        Map<String, Object> res = new HashMap<>();
        res.put("status", "completed");
        res.put("durationSeconds", seconds);
        res.put("event", (event != null && !event.isBlank()) ? event : "cpu");
        res.put("profilerOutput", stopMessage);
        res.put("flamegraphUrl", "/api/profiler/flamegraph");
        return res;
    }
}
