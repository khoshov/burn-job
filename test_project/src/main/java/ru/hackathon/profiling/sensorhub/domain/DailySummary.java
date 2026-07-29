package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.*;
import java.time.LocalDate;

@Entity
@Table(name = "daily_summary", indexes = {
        @Index(name = "ix_daily_station_date", columnList = "station_id, summary_date")
})
public class DailySummary {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "station_id", nullable = false)
    private Long stationId;

    @Column(name = "summary_date", nullable = false)
    private LocalDate summaryDate;

    @Column(nullable = false)
    private long samples;

    @Column(name = "avg_measured")
    private Double avgMeasured;

    @Column(name = "max_measured")
    private Double maxMeasured;

    public DailySummary() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getStationId() { return stationId; }
    public void setStationId(Long stationId) { this.stationId = stationId; }

    public LocalDate getSummaryDate() { return summaryDate; }
    public void setSummaryDate(LocalDate summaryDate) { this.summaryDate = summaryDate; }

    public long getSamples() { return samples; }
    public void setSamples(long samples) { this.samples = samples; }

    public Double getAvgMeasured() { return avgMeasured; }
    public void setAvgMeasured(Double avgMeasured) { this.avgMeasured = avgMeasured; }

    public Double getMaxMeasured() { return maxMeasured; }
    public void setMaxMeasured(Double maxMeasured) { this.maxMeasured = maxMeasured; }
}
