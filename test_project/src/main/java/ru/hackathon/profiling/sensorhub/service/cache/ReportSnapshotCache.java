package ru.hackathon.profiling.sensorhub.service.cache;

import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.dto.SnapshotDto;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;

@Service
public class ReportSnapshotCache {

    @Cacheable(value = "reportSnapshots", key = "#key")
    public SnapshotDto getSnapshot(String key) {
        if (key == null || key.isBlank() || key.length() > 256) {
            throw new ApiException("VALIDATION_FAILED", "Key must be non-empty and <= 256 characters", HttpStatus.BAD_REQUEST);
        }

        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digestBytes = md.digest(key.getBytes(StandardCharsets.UTF_8));
            String digest = HexFormat.of().formatHex(digestBytes);
            long payloadSize = 10000L + Math.abs(key.hashCode() % 5000);

            return new SnapshotDto(key, digest, payloadSize, Instant.now());
        } catch (Exception e) {
            throw new ApiException("INTERNAL_ERROR", "Digest error: " + e.getMessage(), HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
