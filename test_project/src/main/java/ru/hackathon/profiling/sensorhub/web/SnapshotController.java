package ru.hackathon.profiling.sensorhub.web;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.hackathon.profiling.sensorhub.service.cache.ReportSnapshotCache;
import ru.hackathon.profiling.sensorhub.web.dto.SnapshotDto;

@RestController
@RequestMapping("/api/reports")
public class SnapshotController {

    private final ReportSnapshotCache snapshotCache;

    public SnapshotController(ReportSnapshotCache snapshotCache) {
        this.snapshotCache = snapshotCache;
    }

    @GetMapping("/snapshot")
    public SnapshotDto getSnapshot(@RequestParam String key) {
        return snapshotCache.getSnapshot(key);
    }
}
