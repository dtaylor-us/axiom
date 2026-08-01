package com.archon.api.domain.repository;

import com.archon.api.domain.model.PasswordResetToken;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Repository for password reset tokens and reset-rate lookups.
 */
@Repository
public interface PasswordResetTokenRepository extends JpaRepository<PasswordResetToken, UUID> {

    /**
     * Finds valid unused tokens for a user.
     *
     * @param userId the owning user id
     * @param now the current time
     * @return valid unused tokens for the user
     */
    List<PasswordResetToken> findByUser_IdAndUsedAtIsNullAndExpiresAtAfter(
            UUID userId,
            Instant now
    );

    /**
     * Counts recent reset requests for per-user rate limiting.
     *
     * @param userId the owning user id
     * @param since lower time bound
     * @return matching request count
     */
    long countByUser_IdAndCreatedAtAfter(UUID userId, Instant since);

    /**
     * Returns all recent tokens so bcrypt matching can determine whether a raw
     * token is valid, expired, or already consumed without ever storing the raw value.
     *
     * @param cutoff earliest creation timestamp to inspect
     * @return recent tokens ordered newest-first
     */
    @Query("""
        SELECT t FROM PasswordResetToken t
        JOIN FETCH t.user
        WHERE t.createdAt > :cutoff
        ORDER BY t.createdAt DESC
        """)
    List<PasswordResetToken> findRecentTokens(@Param("cutoff") Instant cutoff);

    /**
     * Returns recent unused tokens for read-only validation checks.
     *
     * @param cutoff earliest creation timestamp to inspect
     * @return recent unused tokens ordered newest-first
     */
    @Query("""
        SELECT t FROM PasswordResetToken t
        JOIN FETCH t.user
        WHERE t.usedAt IS NULL
        AND t.createdAt > :cutoff
        ORDER BY t.createdAt DESC
        """)
    List<PasswordResetToken> findRecentUnusedTokens(@Param("cutoff") Instant cutoff);
}
