package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.hackathon.profiling.sensorhub.domain.DailySummary;

public interface DailySummaryRepository extends JpaRepository<DailySummary, Long> {
}
