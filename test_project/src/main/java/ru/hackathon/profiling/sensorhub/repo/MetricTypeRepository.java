package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.hackathon.profiling.sensorhub.domain.MetricType;

public interface MetricTypeRepository extends JpaRepository<MetricType, String> {
}
