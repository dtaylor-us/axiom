package com.aiarchitect.api;

import com.aiarchitect.api.domain.model.PasswordResetToken;
import com.aiarchitect.api.domain.model.User;
import com.aiarchitect.api.domain.repository.PasswordResetTokenRepository;
import com.aiarchitect.api.domain.repository.UserRepository;
import com.aiarchitect.api.service.EmailService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.reactive.server.WebTestClient;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.http.HttpHeaders.RETRY_AFTER;

class PasswordResetControllerIntegrationTest extends AbstractIntegrationTest {

    private static final String RESET_REQUEST_SUCCESS_MESSAGE =
            "If an account exists for this email address, a password reset link has been sent. The link expires in 30 minutes.";

    @Autowired
    private WebTestClient webTestClient;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordResetTokenRepository tokenRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @MockBean
    private EmailService emailService;

    @BeforeEach
    void setUp() {
        tokenRepository.deleteAll();
        userRepository.deleteAll();
    }

    @Test
    void forgotPassword_returns200ForUnknownEmailWithSameMessageAsKnownEmail() {
        userRepository.save(user("known@test.com", "CurrentPassword123"));

        webTestClient.post()
                .uri("/api/v1/auth/forgot-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"known@test.com\"}")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.message").isEqualTo(RESET_REQUEST_SUCCESS_MESSAGE);

        webTestClient.post()
                .uri("/api/v1/auth/forgot-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"missing@test.com\"}")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.message").isEqualTo(RESET_REQUEST_SUCCESS_MESSAGE);
    }

    @Test
    void forgotPassword_returns200ForKnownEmail() {
        userRepository.save(user("known@test.com", "CurrentPassword123"));

        webTestClient.post()
                .uri("/api/v1/auth/forgot-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"known@test.com\"}")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.message").isEqualTo(RESET_REQUEST_SUCCESS_MESSAGE);
    }

    @Test
    void forgotPassword_returns429AfterRateLimitExceededWithRetryAfterHeader() {
        userRepository.save(user("known@test.com", "CurrentPassword123"));

        for (int attempt = 0; attempt < 3; attempt++) {
            webTestClient.post()
                    .uri("/api/v1/auth/forgot-password")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue("{\"email\":\"known@test.com\"}")
                    .exchange()
                    .expectStatus().isOk();
        }

        webTestClient.post()
                .uri("/api/v1/auth/forgot-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"known@test.com\"}")
                .exchange()
                .expectStatus().isEqualTo(429)
                .expectHeader().valueEquals(RETRY_AFTER, "3600")
                .expectBody()
                .jsonPath("$.error").isEqualTo("rate_limit_exceeded");
    }

    @Test
    void forgotPassword_requiresValidEmailFormat() {
        webTestClient.post()
                .uri("/api/v1/auth/forgot-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"not-an-email\"}")
                .exchange()
                .expectStatus().isBadRequest();
    }

    @Test
    void resetPassword_returns200WithValidToken() {
        User user = userRepository.save(user("known@test.com", "CurrentPassword123"));
        String rawToken = "a".repeat(64);
        tokenRepository.save(validToken(user, rawToken, Instant.now().plus(30, ChronoUnit.MINUTES), null));

        webTestClient.post()
                .uri("/api/v1/auth/reset-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("""
                        {
                          "token": "%s",
                          "newPassword": "NewSecurePassword123",
                          "confirmPassword": "NewSecurePassword123"
                        }
                        """.formatted(rawToken))
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.message").value(containsString("Your password has been reset"));
    }

    @Test
    void resetPassword_returns410WithExpiredToken() {
        User user = userRepository.save(user("known@test.com", "CurrentPassword123"));
        String rawToken = "a".repeat(64);
        tokenRepository.save(validToken(user, rawToken, Instant.now().minus(1, ChronoUnit.MINUTES), null));

        webTestClient.post()
                .uri("/api/v1/auth/reset-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("""
                        {
                          "token": "%s",
                          "newPassword": "NewSecurePassword123",
                          "confirmPassword": "NewSecurePassword123"
                        }
                        """.formatted(rawToken))
                .exchange()
                .expectStatus().isEqualTo(410)
                .expectBody()
                .jsonPath("$.error").isEqualTo("invalid_token");
    }

    @Test
    void resetPassword_returns400WhenPasswordsDoNotMatch() {
        webTestClient.post()
                .uri("/api/v1/auth/reset-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("""
                        {
                          "token": "%s",
                          "newPassword": "NewSecurePassword123",
                          "confirmPassword": "MismatchPassword456"
                        }
                        """.formatted("a".repeat(64)))
                .exchange()
                .expectStatus().isBadRequest()
                .expectBody()
                .jsonPath("$.error").isEqualTo("password_mismatch");
    }

    @Test
    void resetPassword_returns400WhenPasswordTooShort() {
        webTestClient.post()
                .uri("/api/v1/auth/reset-password")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("""
                        {
                          "token": "%s",
                          "newPassword": "shortpass",
                          "confirmPassword": "shortpass"
                        }
                        """.formatted("a".repeat(64)))
                .exchange()
                .expectStatus().isBadRequest()
                .expectBody()
                .jsonPath("$.detail").value(containsString("newPassword"));
    }

    @Test
    void validateToken_returnsValidTrueForValidToken() {
        User user = userRepository.save(user("known@test.com", "CurrentPassword123"));
        String rawToken = "a".repeat(64);
        tokenRepository.save(validToken(user, rawToken, Instant.now().plus(30, ChronoUnit.MINUTES), null));

        webTestClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/api/v1/auth/reset-password/validate")
                        .queryParam("token", rawToken)
                        .build())
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.valid").isEqualTo(true);
    }

    @Test
    void validateToken_returnsValidFalseAnd410ForExpiredToken() {
        User user = userRepository.save(user("known@test.com", "CurrentPassword123"));
        String rawToken = "a".repeat(64);
        tokenRepository.save(validToken(user, rawToken, Instant.now().minus(1, ChronoUnit.MINUTES), null));

        webTestClient.get()
                .uri(uriBuilder -> uriBuilder
                        .path("/api/v1/auth/reset-password/validate")
                        .queryParam("token", rawToken)
                        .build())
                .exchange()
                .expectStatus().isEqualTo(410)
                .expectBody()
                .jsonPath("$.valid").isEqualTo(false);
    }

    private User user(String email, String rawPassword) {
        return User.builder()
                .email(email)
                .password(passwordEncoder.encode(rawPassword))
                .name("User")
                .build();
    }

    private PasswordResetToken validToken(
            User user,
            String rawToken,
            Instant expiresAt,
            Instant usedAt
    ) {
        return PasswordResetToken.builder()
                .user(user)
                .tokenHash(passwordEncoder.encode(rawToken))
                .expiresAt(expiresAt)
                .usedAt(usedAt)
                .requestIp("127.0.0.1")
                .userAgent("JUnit")
                .build();
    }
}
