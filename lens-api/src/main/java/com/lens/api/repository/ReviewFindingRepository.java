package com.lens.api.repository;

import com.lens.api.domain.model.ReviewFinding;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface ReviewFindingRepository extends JpaRepository<ReviewFinding, UUID> {

    List<ReviewFinding> findByReportId(UUID reportId);

    void deleteByReportId(UUID reportId);
}
