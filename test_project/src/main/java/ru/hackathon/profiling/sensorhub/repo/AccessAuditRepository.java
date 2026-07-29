package ru.hackathon.profiling.sensorhub.repo;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import ru.hackathon.profiling.sensorhub.domain.AccessAudit;

import java.util.List;

public interface AccessAuditRepository extends JpaRepository<AccessAudit, Long> {

    @Query("SELECT a FROM AccessAudit a ORDER BY a.loggedAt DESC")
    List<AccessAudit> findRecent(Pageable pageable);
}
