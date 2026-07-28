package com.example.badhibernate.controller;

import com.example.badhibernate.service.ProfilerService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/profiler")
public class ProfilerController {

    private final ProfilerService profilerService;

    public ProfilerController(ProfilerService profilerService) {
        this.profilerService = profilerService;
    }

    @GetMapping("/status")
    public Map<String, Object> getStatus() {
        Map<String, Object> result = new HashMap<>();
        result.put("available", profilerService.isAvailable());
        result.put("status", profilerService.getStatus());
        return result;
    }

    @PostMapping("/start")
    public ResponseEntity<Map<String, String>> startProfiling(
            @RequestParam(defaultValue = "cpu") String event,
            @RequestParam(defaultValue = "1000000") Long intervalNs) {
        try {
            String output = profilerService.start(event, intervalNs);
            Map<String, String> res = new HashMap<>();
            res.put("message", "Profiler started");
            res.put("output", output);
            return ResponseEntity.ok(res);
        } catch (Exception e) {
            Map<String, String> err = new HashMap<>();
            err.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(err);
        }
    }

    @PostMapping("/stop")
    public ResponseEntity<Map<String, String>> stopProfiling() {
        try {
            String output = profilerService.stopAndGenerateFlamegraph();
            Map<String, String> res = new HashMap<>();
            res.put("message", "Profiler stopped and flamegraph generated");
            res.put("output", output);
            res.put("flamegraphUrl", "/api/profiler/flamegraph");
            return ResponseEntity.ok(res);
        } catch (Exception e) {
            Map<String, String> err = new HashMap<>();
            err.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(err);
        }
    }

    @GetMapping(value = "/flamegraph", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> getFlamegraph() throws IOException {
        String html = profilerService.getLatestFlamegraphHtml();
        return ResponseEntity.ok().contentType(MediaType.TEXT_HTML).body(html);
    }

    @PostMapping("/profile")
    public ResponseEntity<Map<String, Object>> profileTimed(
            @RequestParam(defaultValue = "5") int duration,
            @RequestParam(defaultValue = "cpu") String event) {
        try {
            Map<String, Object> res = profilerService.profileForDuration(duration, event);
            return ResponseEntity.ok(res);
        } catch (Exception e) {
            Map<String, Object> err = new HashMap<>();
            err.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(err);
        }
    }
}
