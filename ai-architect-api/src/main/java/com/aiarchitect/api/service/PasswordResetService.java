package com.aiarchitect.api.service;

import com.aiarchitect.api.domain.model.PasswordResetToken;
import com.aiarchitect.api.domain.model.User;
import com.aiarchitect.api.domain.repository.PasswordResetTokenRepository;
import com.aiarchitect.api.domain.repository.UserRepository;
import com.aiarchitect.api.exception.InvalidResetTokenException;
import com.aiarchitect.api.exception.PasswordValidationException;
import com.aiarchitect.api.exception.RateLimitExceededException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * Handles the password-reset lifecycle from request to token consumption.
 *
 * Tokens are generated with `SecureRandom`, stored as bcrypt hashes only,
 * expire after 30 minutes, and are consumed in the same transaction that
 * updates the user password.
 *
 * @author OpenAI
 */
@Service
@Slf4j
@RequiredArgsConstructor
@Transactional
public class PasswordResetService {

    private static final int TOKEN_EXPIRY_MINUTES = 30;
    private static final int MAX_REQUESTS_PER_HOUR = 3;
    private static final int TOKEN_BYTES = 32;
    private static final int MIN_PASSWORD_LENGTH = 12;
    private static final int USER_AGENT_MAX_LENGTH = 200;
    private static final int TOKEN_LOOKUP_FUZZ_MINUTES = 5;
    private static final java.security.SecureRandom SECURE_RANDOM =
            new java.security.SecureRandom();
    private static final Pattern AUTO_LOCAL_EMAIL_PATTERN =
            Pattern.compile("^[^@]+@auto\\.local$", Pattern.CASE_INSENSITIVE);

    private final UserRepository userRepository;
    private final PasswordResetTokenRepository tokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final EmailService emailService;

    /**
     * Creates a reset token for a known, resettable user and sends the email.
     *
     * Unknown and synthetic guest-style emails return silently so the HTTP layer
     * can always respond with the same generic success message.
     *
     * @param email user-supplied email address
     * @param requestIp request IP for audit logging
     * @param userAgent user agent for audit logging
     * @throws RateLimitExceededException when too many requests have been made recently
     */
    public void requestReset(String email, String requestIp, String userAgent) {
        log.info("Password reset requested. email=[REDACTED] ip={}", requestIp);

        String normalizedEmail = normalizeEmail(email);
        if (normalizedEmail.isEmpty()) {
            return;
        }

        Optional<User> userOpt = userRepository.findByEmailIgnoreCase(normalizedEmail);
        if (userOpt.isEmpty()) {
            log.info("Password reset requested for unknown account. email=[REDACTED] ip={}", requestIp);
            return;
        }

        User user = userOpt.get();
        if (!isResettableUser(user)) {
            log.info("Password reset skipped for synthetic account. userId={} ip={}", user.getId(), requestIp);
            return;
        }

        Instant oneHourAgo = Instant.now().minus(1, ChronoUnit.HOURS);
        long recentRequests = tokenRepository.countByUser_IdAndCreatedAtAfter(user.getId(), oneHourAgo);
        if (recentRequests >= MAX_REQUESTS_PER_HOUR) {
            log.warn("Password reset rate limit exceeded. userId={} ip={}", user.getId(), requestIp);
            throw new RateLimitExceededException(
                    "Too many requests. Please wait before trying again."
            );
        }

        String rawToken = generateRawToken();
        PasswordResetToken resetToken = PasswordResetToken.builder()
                .user(user)
                .tokenHash(passwordEncoder.encode(rawToken))
                .expiresAt(Instant.now().plus(TOKEN_EXPIRY_MINUTES, ChronoUnit.MINUTES))
                .requestIp(requestIp)
                .userAgent(sanitizeUserAgent(userAgent))
                .build();
        tokenRepository.save(resetToken);

        log.info("Password reset token created. userId={} tokenId={} ip={}",
                user.getId(), resetToken.getId(), requestIp);

        emailService.sendPasswordResetEmail(user.getEmail(), rawToken);
    }

    /**
     * Resets a user's password for a matching unexpired, unused token.
     *
     * @param rawToken token from the emailed reset link
     * @param newPassword new password candidate
     * @throws InvalidResetTokenException when the token is not valid anymore
     * @throws PasswordValidationException when the new password breaks policy
     */
    public void resetPassword(String rawToken, String newPassword) {
        validateNewPassword(newPassword);

        PasswordResetToken matched = findRecentTokens()
                .stream()
                .filter(token -> passwordEncoder.matches(rawToken, token.getTokenHash()))
                .findFirst()
                .orElseThrow(() -> {
                    log.warn("Password reset rejected. reason=not_found");
                    return new InvalidResetTokenException(
                            "This reset link is invalid or has expired. Please request a new password reset."
                    );
                });

        if (matched.isExpired()) {
            log.warn("Password reset rejected. tokenId={} reason=expired", matched.getId());
            throw new InvalidResetTokenException(
                    "This reset link has expired or has already been used. Please request a new password reset."
            );
        }

        if (matched.isUsed()) {
            log.warn("Password reset rejected. tokenId={} reason=used", matched.getId());
            throw new InvalidResetTokenException(
                    "This reset link has expired or has already been used. Please request a new password reset."
            );
        }

        User user = matched.getUser();
        if (passwordEncoder.matches(newPassword, user.getPassword())) {
            throw new PasswordValidationException(
                    "New password must be different from your current password."
            );
        }

        user.setPassword(passwordEncoder.encode(newPassword));
        userRepository.save(user);

        matched.setUsedAt(Instant.now());
        tokenRepository.save(matched);

        log.info("Password reset completed. userId={} tokenId={}", user.getId(), matched.getId());
    }

    /**
     * Validates a token without consuming it so the UI can render an expiry state.
     *
     * @param rawToken token from the emailed reset link
     * @return true when a matching unused, unexpired token exists
     */
    @Transactional(readOnly = true)
    public boolean isTokenValid(String rawToken) {
        if (rawToken == null || rawToken.isBlank()) {
            return false;
        }

        return tokenRepository.findRecentUnusedTokens(tokenCutoff())
                .stream()
                .filter(PasswordResetToken::isValid)
                .anyMatch(token -> passwordEncoder.matches(rawToken, token.getTokenHash()));
    }

    private void validateNewPassword(String password) {
        if (password == null || password.length() < MIN_PASSWORD_LENGTH) {
            throw new PasswordValidationException(
                    "Password must be at least " + MIN_PASSWORD_LENGTH + " characters."
            );
        }
    }

    private List<PasswordResetToken> findRecentTokens() {
        return tokenRepository.findRecentTokens(tokenCutoff());
    }

    private Instant tokenCutoff() {
        return Instant.now().minus(TOKEN_EXPIRY_MINUTES + TOKEN_LOOKUP_FUZZ_MINUTES, ChronoUnit.MINUTES);
    }

    private String sanitizeUserAgent(String userAgent) {
        if (userAgent == null || userAgent.isBlank()) {
            return null;
        }
        return userAgent.substring(0, Math.min(userAgent.length(), USER_AGENT_MAX_LENGTH));
    }

    private String generateRawToken() {
        byte[] tokenBytes = new byte[TOKEN_BYTES];
        SECURE_RANDOM.nextBytes(tokenBytes);
        return HexFormat.of().formatHex(tokenBytes);
    }

    private boolean isResettableUser(User user) {
        return user.getEmail() != null && !AUTO_LOCAL_EMAIL_PATTERN.matcher(user.getEmail()).matches();
    }

    private String normalizeEmail(String email) {
        return email == null ? "" : email.trim().toLowerCase();
    }
}
