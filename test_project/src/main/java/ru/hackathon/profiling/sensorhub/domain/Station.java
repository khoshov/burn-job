package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "station", indexes = {
        @Index(name = "ix_station_region", columnList = "region")
})
public class Station {

    @Id
    private Long id;

    @Column(nullable = false, unique = true, length = 32)
    private String code;

    @Column(nullable = false, length = 128)
    private String title;

    @Column(nullable = false, length = 64)
    private String region;

    @Column(nullable = false)
    private boolean active = true;

    @Column(nullable = false)
    private LocalDate installedOn;

    @OneToMany(mappedBy = "station", fetch = FetchType.LAZY)
    private List<Measurement> measurements = new ArrayList<>();

    public Station() {}

    public Station(Long id, String code, String title, String region, boolean active, LocalDate installedOn) {
        this.id = id;
        this.code = code;
        this.title = title;
        this.region = region;
        this.active = active;
        this.installedOn = installedOn;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getRegion() { return region; }
    public void setRegion(String region) { this.region = region; }

    public boolean isActive() { return active; }
    public void setActive(boolean active) { this.active = active; }

    public LocalDate getInstalledOn() { return installedOn; }
    public void setInstalledOn(LocalDate installedOn) { this.installedOn = installedOn; }

    public List<Measurement> getMeasurements() { return measurements; }
    public void setMeasurements(List<Measurement> measurements) { this.measurements = measurements; }
}
