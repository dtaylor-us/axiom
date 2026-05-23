package com.aiarchitect.api.service;

import com.aiarchitect.api.domain.model.PasswordResetToken;
import com.aiarchitect.api.domain.model.User;
import com.aiarchitect.api.domain.repository.PasswordResetTokenRepository;
import com.aiarchitect.api.domain.repository.UserRepository;
import com.aiarchitect.api.exception.InvalidResetTokenException;
import com.aiarchitect.api.exception.PasswordValidationException;
import com.aiarchitect.api.exception.RateLimitExceededException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PasswordResetServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordResetTokenRepository tokenRepository;

    @Mock
    private EmailService emailService;

    @Captor
    private ArgumentCaptor<PasswordResetToken> tokenCaptor;

    @Captor
    private ArgumentCaptor<User> userCaptor;

    @Captor
    private ArgumentCaptor<String> rawTokenCaptor;

    private PasswordEncoder passwordEncoder;
    private PasswordResetService service;

    @BeforeEach
    void setUp() {
        passwordEncoder = new BCryptPasswordEncoder();
        service = new PasswordResetService(
                userRepository,
                tokenRepository,
                passwordEncoder,
                emailService
        );
    }

    @Test
    void requestReset_createsTokenAndSendsEmailForKnownEmail() {
        User user = user("known@test.com", "CurrentPassword123");
        when(userRepository.findByEmailIgnoreCase("known@test.com"))
                .thenReturn(Optional.of(user));
        when(tokenRepository.countByUser_IdAndCreatedAtAfter(any(UUID.class), any(Instant.class)))
                .thenReturn(0L);
        when(tokenRepository.save(any(PasswordResetToken.class))).thenAnswer(invocation -> {
            PasswordResetToken token = invocation.getArgument(0);
            token.setId(UUID.randomUUID());
            return token;
        });

        service.requestReset("known@test.com", "127.0.0.1", "JUnit");

        verify(tokenRepository).save(tokenCaptor.capture());
        verify(emailService).sendPasswordResetEmail(anyString(), rawTokenCaptor.capture());

        assertThat(tokenCaptor.getValue().getUser()).isEqualTo(user);
        assertThat(rawTokenCaptor.getValue()).isNotBlank();
    }

    @Test
    void requestReset_returnsSilentlyForUnknownEmailWithoutThrowingOrSendingEmail() {
        when(userRepository.findByEmailIgnoreCase("missing@test.com"))
                .thenReturn(Optional.empty());

        service.requestReset("missing@test.com", "127.0.0.1", "JUnit");

        verify(tokenRepository, never()).save(any());
        verify(emailService, never()).sendPasswordResetEmail(anyString(), anyString());
    }

    @Test
    void requestReset_throwsRateLimitExceededExceptionWhenThreeRequestsExist() {
        User user = user("known@test.com", "CurrentPassword123");
        when(userRepository.findByEmailIgnoreCase("known@test.com"))
                .thenReturn(Optional.of(user));
        when(tokenRepository.countByUser_IdAndCreatedAtAfter(any(UUID.class), any(Instant.class)))
                .thenReturn(3L);

        assertThatThrownBy(() -> service.requestReset("known@test.com", "127.0.0.1", "JUnit"))
                .isInstanceOf(RateLimitExceededException.class)
                .hasMessageContaining("Too many requests");
    }

    @Test
    void requestReset_usesSecureRandomToProduceSixtyFourHexCharacters() {
        User user = user("known@test.com", "CurrentPassword123");
        when(userRepository.findByEmailIgnoreCase("known@test.com"))
                .thenReturn(Optional.of(user));
        when(tokenRepository.countByUser_IdAndCreatedAtAfter(any(UUID.class), any(Instant.class)))
                .thenReturn(0L);
        when(tokenRepository.save(any(PasswordResetToken.class))).thenAnswer(invocation -> {
            PasswordResetToken token = invocation.getArgument(0);
            token.setId(UUID.randomUUID());
            return token;
        });

        service.requestReset("known@test.com", "127.0.0.1", "JUnit");

        verify(emailService).sendPasswordResetEmail(anyString(), rawTokenCaptor.capture());
        assertThat(rawTokenCaptor.getValue()).matches("^[0-9a-f]{64}$");
    }

    @Test
    void requestReset_storesBcryptHashNotRawToken() {
        User user = user("known@test.com", "CurrentPassword123");
        when(userRepository.findByEmailIgnoreCase("known@test.com"))
                .thenReturn(Optional.of(user));
        when(tokenRepository.countByUser_IdAndCreatedAtAfter(any(UUID.class), any(Instant.class)))
                .thenReturn(0L);
        when(tokenRepository.save(any(PasswordResetToken.class))).thenAnswer(invocation -> {
            PasswordResetToken token = invocation.getArgument(0);
            token.setId(UUID.randomUUID());
            return token;
        });

        service.requestReset("known@test.com", "127.0.0.1", "JUnit");

        verify(tokenRepository).save(tokenCaptor.capture());
        verify(emailService).sendPasswordResetEmail(anyString(), rawTokenCaptor.capture());

        assertThat(tokenCaptor.getValue().getTokenHash()).isNotEqualTo(rawTokenCaptor.getValue());
        assertThat(passwordEncoder.matches(
                rawTokenCaptor.getValue(),
                tokenCaptor.getValue().getTokenHash()
        )).isTrue();
    }

    @Test
    void requestReset_setsExpiryToThirtyMinutesFromNow() {
        User user = user("known@test.com", "CurrentPassword123");
        when(userRepository.findByEmailIgnoreCase("known@test.com"))
                .thenReturn(Optional.of(user));
        when(tokenRepository.countByUser_IdAndCreatedAtAfter(any(UUID.class), any(Instant.class)))
                .thenReturn(0L);
        when(tokenRepository.save(any(PasswordResetToken.class))).thenAnswer(invocation -> {
            PasswordResetToken token = invocation.getArgument(0);
            token.setId(UUID.randomUUID());
            return token;
        });
        Instant before = Instant.now();

        service.requestReset("known@test.com", "127.0.0.1", "JUnit");

        Instant after = Instant.now();
        verify(tokenRepository).save(tokenCaptor.capture());
        assertThat(tokenCaptor.getValue().getExpiresAt())
                .isAfter(before.plus(29, ChronoUnit.MINUTES))
                .isBefore(after.plus(31, ChronoUnit.MINUTES));
    }

    @Test
    void resetPassword_successfullyResetsPasswordWithValidToken() {
        User user = user("known@test.com", "CurrentPassword123");
        String rawToken = "a".repeat(64);
        PasswordResetToken storedToken = validToken(user, rawToken);
        when(tokenRepository.findRecentTokens(any(Instant.class)))
                .thenReturn(List.of(storedToken));
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.resetPassword(rawToken, "NewSecurePassword123");

        verify(userRepository).save(userCaptor.capture());
        assertThat(passwordEncoder.matches(
                "NewSecurePassword123",
                userCaptor.getValue().getPassword()
        )).isTrue();
    }

    @Test
    void resetPassword_throwsInvalidResetTokenExceptionWhenTokenDoesNotMatchAnyStoredHash() {
        User user = user("known@test.com", "CurrentPassword123");
        PasswordResetToken storedToken = validToken(user, "b".repeat(64));
        when(tokenRepository.findRecentTokens(any(Instant.class)))
                .thenReturn(List.of(storedToken));

        assertThatThrownBy(() -> service.resetPassword("a".repeat(64), "NewSecurePassword123"))
                .isInstanceOf(InvalidResetTokenException.class)
                .hasMessageContaining("invalid or has expired");
    }

    @Test
    void resetPassword_throwsInvalidResetTokenExceptionWhenTokenIsExpired() {
        User user = user("known@test.com", "CurrentPassword123");
        String rawToken = "a".repeat(64);
        PasswordResetToken storedToken = validToken(user, rawToken);
        storedToken.setExpiresAt(Instant.now().minus(1, ChronoUnit.MINUTES));
        when(tokenRepository.findRecentTokens(any(Instant.class)))
                .thenReturn(List.of(storedToken));

        assertThatThrownBy(() -> service.resetPassword(rawToken, "NewSecurePassword123"))
                .isInstanceOf(InvalidResetTokenException.class)
                .hasMessageContaining("already been used");
    }

    @Test
    void resetPassword_throwsInvalidResetTokenExceptionWhenTokenAlreadyUsed() {
        User user = user("known@test.com", "CurrentPassword123");
        String rawToken = "a".repeat(64);
        PasswordResetToken storedToken = validToken(user, rawToken);
        storedToken.setUsedAt(Instant.now().minus(1, ChronoUnit.MINUTES));
        when(tokenRepository.findRecentTokens(any(Instant.class)))
                .thenReturn(List.of(storedToken));

        assertThatThrownBy(() -> service.resetPassword(rawToken, "NewSecurePassword123"))
                .isInstanceOf(InvalidResetTokenException.class)
                .hasMessageContaining("already been used");
    }

    @Test
    void resetPassword_marksTokenUsedAfterSuccessfulReset() {
        User user = user("known@test.com", "CurrentPassword123");
        String rawToken = "a".repeat(64);
        PasswordResetToken storedToken = validToken(user, rawToken);
        when(tokenRepository.findRecentTokens(any(Instant.class)))
                .thenReturn(List.of(storedToken));

        service.resetPassword(rawToken, "NewSecurePassword123");

        verify(tokenRepository).save(tokenCaptor.capture());
        assertThat(tokenCaptor.getValue().getUsedAt()).isNotNull();
    }

    @Test
    void resetPassword_throwsPasswordValidationExceptionWhenNewPasswordMatchesCurrentPassword() {
        User user = user("known@test.com", "CurrentPassword123");
        String rawToken = "a".repeat(64);
        PasswordResetToken storedToken = validToken(user, rawToken);
        when(tokenRepository.findRecentTokens(any(Instant.class)))
                .thenReturn(List.of(storedToken));

        assertThatThrownBy(() -> service.resetPassword(rawToken, "CurrentPassword123"))
                .isInstanceOf(PasswordValidationException.class)
                .hasMessageContaining("different from your current password");
    }

    @Test
    void resetPassword_throwsPasswordValidationExceptionWhenNewPasswordIsUnderTwelveCharacters() {
        assertThatThrownBy(() -> service.resetPassword("a".repeat(64), "short-pass"))
                .isInstanceOf(PasswordValidationException.class)
                .hasMessageContaining("at least 12 characters");
    }

    private User user(String email, String rawPassword) {
        return User.builder()
                .id(UUID.randomUUID())
                .email(email)
                .password(passwordEncoder.encode(rawPassword))
                .name("User")
                .build();
    }

    private PasswordResetToken validToken(User user, String rawToken) {
        return PasswordResetToken.builder()
                .id(UUID.randomUUID())
                .user(user)
                .tokenHash(passwordEncoder.encode(rawToken))
                .expiresAt(Instant.now().plus(30, ChronoUnit.MINUTES))
                .createdAt(Instant.now())
                .build();
    }
}
