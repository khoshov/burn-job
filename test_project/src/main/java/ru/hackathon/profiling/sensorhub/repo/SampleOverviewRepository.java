package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ru.hackathon.profiling.sensorhub.domain.RawSample;

import java.time.Instant;
import java.util.List;

public interface SampleOverviewRepository extends JpaRepository<RawSample, Long> {

    @Query("SELECT COUNT(r), AVG(r.measured), MAX(r.measured) FROM RawSample r WHERE " +
           "(:from IS NULL OR r.takenAt >= :from) AND " +
           "(:to IS NULL OR r.takenAt <= :to)")
    List<Object[]> getOverviewStats(@Param("from") Instant from, @Param("to") Instant to);

    @Query("SELECT r FROM RawSample r WHERE r.metricCode = :metric ORDER BY r.measured DESC, r.stationId ASC")
    List<RawSample> findTopByMetric(@Param("metric") String metric, Pageable pageable);
}
