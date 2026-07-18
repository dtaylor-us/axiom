package com.memoria.api.repository;

import com.memoria.api.domain.model.MemoryEntry;
import com.memoria.api.domain.model.MemoryStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public interface MemoryEntryRepository extends JpaRepository<MemoryEntry, UUID>, JpaSpecificationExecutor<MemoryEntry> {
    List<MemoryEntry> findByProjectIdAndStatusOrderByCreatedAtDesc(UUID projectId, MemoryStatus status);
    List<MemoryEntry> findByProjectIdOrderByCreatedAtDesc(UUID projectId);
    List<MemoryEntry> findByExpiresAtBeforeAndStatus(LocalDateTime now, MemoryStatus status);

    /**
     * Returns the IDs of memory entries for the given project whose tags array
     * exactly contains the requested tag using the PostgreSQL {@code @>} array
     * containment operator. This query uses the GIN index on the tags column
     * (created in Flyway V5) rather than the fragile array_to_string+LIKE
     * approach, which bypasses index support and produces incorrect results for
     * tags that are substrings of other tags.
     *
     * @param projectId the project to scope results to
     * @param tag       the exact tag value to match
     * @return set of matching entry IDs
     */
    @Query(
        value = "SELECT id FROM memory_entries WHERE project_id = :projectId AND tags @> CAST(ARRAY[:tag] AS text[])",
        nativeQuery = true
    )
    Set<UUID> findIdsByProjectIdAndTag(@Param("projectId") UUID projectId, @Param("tag") String tag);
}
