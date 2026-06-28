package com.lens.api.repository;

import com.lens.api.domain.model.ReviewReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface ReviewReportRepository extends JpaRepository<ReviewReport, UUID> {

    Optional<ReviewReport> findBySessionId(UUID sessionId);

    Optional<ReviewReport> findFirstBySessionIdOrderByGeneratedAtDescIdDesc(UUID sessionId);

    void deleteBySessionId(UUID sessionId);
}
