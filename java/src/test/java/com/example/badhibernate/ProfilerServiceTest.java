package com.example.badhibernate;

import com.example.badhibernate.service.ProfilerService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class ProfilerServiceTest {

    @Autowired
    private ProfilerService profilerService;

    @Test
    @DisplayName("Test async-profiler availability and status")
    void testProfilerAvailability() {
        assertNotNull(profilerService, "ProfilerService bean should be loaded");
        if (profilerService.isAvailable()) {
            String status = profilerService.getStatus();
            assertNotNull(status, "Profiler status should not be null");
            System.out.println("AsyncProfiler status: " + status);
        } else {
            System.out.println("AsyncProfiler is not supported on this host environment/OS.");
        }
    }

    @Test
    @DisplayName("Test starting, stopping profiler and generating flamegraph HTML")
    void testStartStopProfiler() throws Exception {
        if (!profilerService.isAvailable()) {
            return;
        }

        String startOutput = profilerService.start("cpu", 1_000_000L);
        assertNotNull(startOutput);

        // Perform CPU calculation work
        double sum = 0;
        for (int i = 0; i < 1_000_000; i++) {
            sum += Math.sin(i);
        }

        String stopOutput = profilerService.stopAndGenerateFlamegraph();
        assertNotNull(stopOutput);

        // Generate sample.jfr and sample.collapsed for testing converters
        profilerService.start("cpu", 1_000_000L);
        for (int i = 0; i < 1_000_000; i++) {
            sum += Math.cos(i);
        }
        try {
            one.profiler.AsyncProfiler.getInstance().execute("stop,file=target/sample_profile.jfr,jfr");
            one.profiler.AsyncProfiler.getInstance().execute("stop,file=target/sample_profile.collapsed,collapsed");
        } catch (Exception ignored) {}

        String html = profilerService.getLatestFlamegraphHtml();
        assertNotNull(html);
        assertTrue(html.length() > 0, "Flamegraph HTML output should not be empty");
    }
}
