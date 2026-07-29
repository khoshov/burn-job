package ru.hackathon.profiling.sensorhub.harness;

import org.springframework.cache.CacheManager;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal")
@Profile({"load", "leak"})
public class InternalOpsController {

    private final JdbcTemplate jdbcTemplate;
    private final CacheManager cacheManager;

    public InternalOpsController(JdbcTemplate jdbcTemplate, CacheManager cacheManager) {
        this.jdbcTemplate = jdbcTemplate;
        this.cacheManager = cacheManager;
    }

    @PostMapping("/reset")
    public ResponseEntity<Void> reset() {
        jdbcTemplate.execute("TRUNCATE import_batch, access_audit, daily_summary RESTART IDENTITY CASCADE");

        for (String name : cacheManager.getCacheNames()) {
            var cache = cacheManager.getCache(name);
            if (cache != null) {
                cache.clear();
            }
        }

        HttpHeaders headers = new HttpHeaders();
        headers.add("X-Reset-Tables", "import_batch,access_audit,daily_summary");
        headers.add("X-Reset-Caches", String.join(",", cacheManager.getCacheNames()));

        return ResponseEntity.noContent().headers(headers).build();
    }
}
