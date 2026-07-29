package ru.hackathon.profiling.sensorhub.support;

import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import ru.hackathon.profiling.sensorhub.domain.AccessAudit;
import ru.hackathon.profiling.sensorhub.repo.AccessAuditRepository;

import java.time.Instant;

@Service
public class AuditWriter {

    private final AccessAuditRepository auditRepository;

    public AuditWriter(AccessAuditRepository auditRepository) {
        this.auditRepository = auditRepository;
    }

    public void logAccess(String path, String httpMethod, int statusCode, long elapsedMs, String correlationId) {
        AccessAudit audit = new AccessAudit();
        audit.setPath(path);
        audit.setHttpMethod(httpMethod);
        audit.setStatusCode(statusCode);
        audit.setElapsedMs(elapsedMs);
        audit.setLoggedAt(Instant.now());
        audit.setCorrelationId(correlationId);
        try {
            auditRepository.save(audit);
        } catch (Exception ignored) {
        }
    }
}
