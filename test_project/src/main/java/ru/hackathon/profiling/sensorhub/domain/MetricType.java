package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "metric_type")
public class MetricType {

    @Id
    @Column(length = 32)
    private String code;

    @Column(nullable = false, length = 128)
    private String title;

    @Column(name = "unit_label", nullable = false, length = 32)
    private String unitLabel;

    @Column(nullable = false)
    private Integer scale;

    public MetricType() {}

    public MetricType(String code, String title, String unitLabel, Integer scale) {
        this.code = code;
        this.title = title;
        this.unitLabel = unitLabel;
        this.scale = scale;
    }

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getUnitLabel() { return unitLabel; }
    public void setUnitLabel(String unitLabel) { this.unitLabel = unitLabel; }

    public Integer getScale() { return scale; }
    public void setScale(Integer scale) { this.scale = scale; }
}
