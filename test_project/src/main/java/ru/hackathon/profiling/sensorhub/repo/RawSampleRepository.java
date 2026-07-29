package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ru.hackathon.profiling.sensorhub.domain.RawSample;

import java.time.Instant;
import java.util.List;

public interface RawSampleRepository extends JpaRepository<RawSample, Long> {

    @Query("SELECT r FROM RawSample r WHERE " +
           "(:stationId IS NULL OR r.stationId = :stationId) AND " +
           "(:metric IS NULL OR r.metricCode = :metric) AND " +
           "(:from IS NULL OR r.takenAt >= :from) AND " +
           "(:to IS NULL OR r.takenAt <= :to) AND " +
           "(:minMeasured IS NULL OR r.measured >= :minMeasured)")
    Page<RawSample> searchSamples(@Param("stationId") Long stationId,
                                  @Param("metric") String metric,
                                  @Param("from") Instant from,
                                  @Param("to") Instant to,
                                  @Param("minMeasured") Double minMeasured,
                                  Pageable pageable);

    @Query("SELECT r FROM RawSample r WHERE " +
           "(:from IS NULL OR r.takenAt >= :from) AND " +
           "(:to IS NULL OR r.takenAt <= :to) AND " +
           "(:metric IS NULL OR r.metricCode = :metric)")
    List<RawSample> findForExport(@Param("from") Instant from,
                                  @Param("to") Instant to,
                                  @Param("metric") String metric,
                                  Pageable pageable);
}
