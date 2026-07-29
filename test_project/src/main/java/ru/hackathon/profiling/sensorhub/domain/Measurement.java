package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "measurement", indexes = {
        @Index(name = "ix_measurement_station_metric_taken", columnList = "station_id, metric_code, taken_at"),
        @Index(name = "ix_measurement_metric_taken", columnList = "metric_code, taken_at")
})
public class Measurement {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "station_id", nullable = false)
    private Station station;

    @Column(name = "station_id", insertable = false, updatable = false)
    private Long stationId;

    @Column(name = "metric_code", nullable = false, length = 32)
    private String metricCode;

    @Column(name = "measured", nullable = false)
    private Double measured;

    @Column(name = "taken_at", nullable = false)
    private Instant takenAt;

    @Column(name = "quality_flag")
    private Integer qualityFlag;

    @Column(name = "note_text")
    private String noteText;

    public Measurement() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Station getStation() { return station; }
    public void setStation(Station station) { this.station = station; }

    public Long getStationId() { return stationId; }

    public String getMetricCode() { return metricCode; }
    public void setMetricCode(String metricCode) { this.metricCode = metricCode; }

    public Double getMeasured() { return measured; }
    public void setMeasured(Double measured) { this.measured = measured; }

    public Instant getTakenAt() { return takenAt; }
    public void setTakenAt(Instant takenAt) { this.takenAt = takenAt; }

    public Integer getQualityFlag() { return qualityFlag; }
    public void setQualityFlag(Integer qualityFlag) { this.qualityFlag = qualityFlag; }

    public String getNoteText() { return noteText; }
    public void setNoteText(String noteText) { this.noteText = noteText; }
}
