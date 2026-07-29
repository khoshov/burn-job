package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ru.hackathon.profiling.sensorhub.domain.Station;

import java.util.Optional;

public interface StationRepository extends JpaRepository<Station, Long> {

    Optional<Station> findByCodeIgnoreCase(String code);

    boolean existsByCode(String code);

    @Query("SELECT s FROM Station s WHERE " +
           "(:query IS NULL OR LOWER(s.code) LIKE LOWER(CONCAT('%', :query, '%')) OR LOWER(s.title) LIKE LOWER(CONCAT('%', :query, '%'))) AND " +
           "(:region IS NULL OR s.region = :region)")
    Page<Station> searchStations(@Param("query") String query, @Param("region") String region, Pageable pageable);
}
