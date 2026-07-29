package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.hackathon.profiling.sensorhub.domain.Measurement;

public interface MeasurementRepository extends JpaRepository<Measurement, Long> {
}
