package com.memoria.api.repository;

import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public interface MemoryEntryRepository extends JpaRepository<MemoryEntry, UUID> {
    List<MemoryEntry> findByProjectIdAndStatusOrderByCreatedAtDesc(UUID projectId, MemoryStatus status);
    List<MemoryEntry> findByProjectIdOrderByCreatedAtDesc(UUID projectId);
    List<MemoryEntry> findByExpiresAtBeforeAndStatus(LocalDateTime now, MemoryStatus status);
}
