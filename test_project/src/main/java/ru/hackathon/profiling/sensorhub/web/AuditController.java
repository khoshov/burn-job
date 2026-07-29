package ru.hackathon.profiling.sensorhub.web;

import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.hackathon.profiling.sensorhub.config.AppProperties;
import ru.hackathon.profiling.sensorhub.repo.AccessAuditRepository;
import ru.hackathon.profiling.sensorhub.web.dto.AuditDto;

import java.util.List;

@RestController
@RequestMapping("/api/audit")
public class AuditController {

    private final AccessAuditRepository accessAuditRepository;
    private final AppProperties appProperties;

    public AuditController(AccessAuditRepository accessAuditRepository, AppProperties appProperties) {
        this.accessAuditRepository = accessAuditRepository;
        this.appProperties = appProperties;
    }

    @GetMapping("/recent")
    public List<AuditDto> getRecentAudit(@RequestParam(defaultValue = "100") int limit) {
        int maxWindow = appProperties.getLimits().getAuditWindow();
        int effectiveLimit = Math.min(limit, maxWindow);

        return accessAuditRepository.findRecent(PageRequest.of(0, effectiveLimit)).stream()
                .map(a -> new AuditDto(
                        a.getPath(),
                        a.getHttpMethod(),
                        a.getStatusCode(),
                        a.getElapsedMs(),
                        a.getLoggedAt(),
                        a.getCorrelationId()
                )).toList();
    }
}
