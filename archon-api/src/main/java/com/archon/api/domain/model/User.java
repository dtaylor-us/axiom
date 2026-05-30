package com.archon.api.domain.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.util.UUID;

/**
 * User entity representing a user in the system.
 */
@Entity
@Table(name = "users")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class User {

    /** Unique identifier for the user, auto-generated as UUID. */
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    /** Unique email address of the user. */
    @Column(unique = true, nullable = false)
    private String email;

    /** Encrypted password of the user. */
    @Column(nullable = false)
    private String password;

    /** Full name of the user. */
    private String name;

    /** Whether the user account is enabled. Defaults to true. */
    @Builder.Default
    @Column(nullable = false)
    private boolean enabled = true;

    /** Timestamp when the user was created. */
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    /** Timestamp when the user was last updated. */
    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;
}
