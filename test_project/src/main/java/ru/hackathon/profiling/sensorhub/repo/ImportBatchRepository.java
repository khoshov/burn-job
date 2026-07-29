package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.hackathon.profiling.sensorhub.domain.ImportBatch;

import java.util.Optional;

public interface ImportBatchRepository extends JpaRepository<ImportBatch, Long> {
    Optional<ImportBatch> findByBatchKey(String batchKey);
}
