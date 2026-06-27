package com.lens.api.repository;

import com.lens.api.domain.model.ReviewRisk;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface ReviewRiskRepository extends JpaRepository<ReviewRisk, UUID> {

    List<ReviewRisk> findByReportId(UUID reportId);

    void deleteByReportId(UUID reportId);
}
