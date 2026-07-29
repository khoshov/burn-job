package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "access_audit", indexes = {
        @Index(name = "ix_audit_logged", columnList = "logged_at")
})
public class AccessAudit {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 256)
    private String path;

    @Column(name = "http_method", nullable = false, length = 16)
    private String httpMethod;

    @Column(name = "status_code", nullable = false)
    private int statusCode;

    @Column(name = "elapsed_ms", nullable = false)
    private long elapsedMs;

    @Column(name = "logged_at", nullable = false)
    private Instant loggedAt;

    @Column(name = "correlation_id", length = 64)
    private String correlationId;

    public AccessAudit() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getPath() { return path; }
    public void setPath(String path) { this.path = path; }

    public String getHttpMethod() { return httpMethod; }
    public void setHttpMethod(String httpMethod) { this.httpMethod = httpMethod; }

    public int getStatusCode() { return statusCode; }
    public void setStatusCode(int statusCode) { this.statusCode = statusCode; }

    public long getElapsedMs() { return elapsedMs; }
    public void setElapsedMs(long elapsedMs) { this.elapsedMs = elapsedMs; }

    public Instant getLoggedAt() { return loggedAt; }
    public void setLoggedAt(Instant loggedAt) { this.loggedAt = loggedAt; }

    public String getCorrelationId() { return correlationId; }
    public void setCorrelationId(String correlationId) { this.correlationId = correlationId; }
}
