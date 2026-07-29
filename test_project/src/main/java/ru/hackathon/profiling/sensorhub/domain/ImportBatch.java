package ru.hackathon.profiling.sensorhub.domain;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "import_batch", indexes = {
        @Index(name = "ux_import_batch_key", columnList = "batch_key", unique = true)
})
public class ImportBatch {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "batch_key", nullable = false, unique = true, length = 128)
    private String batchKey;

    @Column(name = "file_name", nullable = false, length = 256)
    private String fileName;

    @Column(name = "rows_accepted", nullable = false)
    private int rowsAccepted;

    @Column(name = "rows_rejected", nullable = false)
    private int rowsRejected;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "finished_at")
    private Instant finishedAt;

    public ImportBatch() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getBatchKey() { return batchKey; }
    public void setBatchKey(String batchKey) { this.batchKey = batchKey; }

    public String getFileName() { return fileName; }
    public void setFileName(String fileName) { this.fileName = fileName; }

    public int getRowsAccepted() { return rowsAccepted; }
    public void setRowsAccepted(int rowsAccepted) { this.rowsAccepted = rowsAccepted; }

    public int getRowsRejected() { return rowsRejected; }
    public void setRowsRejected(int rowsRejected) { this.rowsRejected = rowsRejected; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }

    public Instant getFinishedAt() { return finishedAt; }
    public void setFinishedAt(Instant finishedAt) { this.finishedAt = finishedAt; }
}
