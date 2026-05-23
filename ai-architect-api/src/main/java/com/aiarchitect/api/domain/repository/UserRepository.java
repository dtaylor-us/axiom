package com.aiarchitect.api.domain.repository;

import com.aiarchitect.api.domain.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

/**
 * Repository interface for User entity.
 * Provides database access and query methods for User records.
 */
@Repository
public interface UserRepository extends JpaRepository<User, UUID> {
    
    /**
     * Finds a user by email address.
     * 
     * @param email the email to search for
     * @return an Optional containing the User if found, empty otherwise
     */
    Optional<User> findByEmail(String email);
    
    /**
     * Checks if a user with the given email exists.
     * 
     * @param email the email to check
     * @return true if a user with this email exists, false otherwise
     */
    boolean existsByEmail(String email);
}
