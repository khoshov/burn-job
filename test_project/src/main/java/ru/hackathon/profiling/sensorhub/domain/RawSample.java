package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "raw_sample", indexes = {
        @Index(name = "ix_raw_station_taken", columnList = "station_id, taken_at"),
        @Index(name = "ix_raw_taken", columnList = "taken_at")
})
public class RawSample {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "station_id", nullable = false)
    private Long stationId;

    @Column(name = "metric_code", nullable = false, length = 32)
    private String metricCode;

    @Column(name = "measured", nullable = false)
    private Double measured;

    @Column(name = "taken_at", nullable = false)
    private Instant takenAt;

    @Column(name = "quality", length = 32)
    private String quality;

    @Column(name = "payload_note")
    private String payloadNote;

    public RawSample() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getStationId() { return stationId; }
    public void setStationId(Long stationId) { this.stationId = stationId; }

    public String getMetricCode() { return metricCode; }
    public void setMetricCode(String metricCode) { this.metricCode = metricCode; }

    public Double getMeasured() { return measured; }
    public void setMeasured(Double measured) { this.measured = measured; }

    public Instant getTakenAt() { return takenAt; }
    public void setTakenAt(Instant takenAt) { this.takenAt = takenAt; }

    public String getQuality() { return quality; }
    public void setQuality(String quality) { this.quality = quality; }

    public String getPayloadNote() { return payloadNote; }
    public void setPayloadNote(String payloadNote) { this.payloadNote = payloadNote; }
}
