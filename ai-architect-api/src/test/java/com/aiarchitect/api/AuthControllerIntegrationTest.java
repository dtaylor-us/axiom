package com.aiarchitect.api;

import com.aiarchitect.api.domain.model.User;
import com.aiarchitect.api.domain.repository.UserRepository;
import com.aiarchitect.api.security.JwtService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.reactive.server.WebTestClient;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(TestcontainersConfig.class)
class AuthControllerIntegrationTest {

    @Autowired private WebTestClient webTestClient;
    @Autowired private UserRepository userRepository;
    @Autowired private PasswordEncoder passwordEncoder;
    @Autowired private JwtService jwtService;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    void register_createsUserAndReturnsToken() {
        webTestClient.post().uri("/api/v1/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"alice@test.com\",\"password\":\"password123\",\"name\":\"Alice\"}")
                .exchange()
                .expectStatus().isCreated()
                .expectBody()
                .jsonPath("$.token").isNotEmpty()
                .jsonPath("$.email").isEqualTo("alice@test.com");

        assertTrue(userRepository.existsByEmail("alice@test.com"));
    }

    @Test
    void register_returns409ForDuplicateEmail() {
        userRepository.save(User.builder()
                .email("dup@test.com")
                .password(passwordEncoder.encode("password123"))
                .name("First")
                .build());

        webTestClient.post().uri("/api/v1/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"dup@test.com\",\"password\":\"password123\",\"name\":\"Second\"}")
                .exchange()
                .expectStatus().is4xxClientError();
    }

    @Test
    void login_returnsTokenForValidCredentials() {
        userRepository.save(User.builder()
                .email("bob@test.com")
                .password(passwordEncoder.encode("password123"))
                .name("Bob")
                .build());

        webTestClient.post().uri("/api/v1/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"bob@test.com\",\"password\":\"password123\"}")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.token").isNotEmpty()
                .jsonPath("$.email").isEqualTo("bob@test.com");
    }

    @Test
    void login_returns401ForWrongPassword() {
        userRepository.save(User.builder()
                .email("carol@test.com")
                .password(passwordEncoder.encode("correctpass"))
                .name("Carol")
                .build());

        webTestClient.post().uri("/api/v1/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"carol@test.com\",\"password\":\"wrongpass1\"}")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void login_returns401ForNonexistentUser() {
        webTestClient.post().uri("/api/v1/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"nobody@test.com\",\"password\":\"password123\"}")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    @Test
    void login_returns403ForDisabledUser() {
        userRepository.save(User.builder()
                .email("disabled@test.com")
                .password(passwordEncoder.encode("password123"))
                .name("Disabled")
                .enabled(false)
                .build());

        webTestClient.post().uri("/api/v1/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"disabled@test.com\",\"password\":\"password123\"}")
                .exchange()
                .expectStatus().isForbidden();
    }

    @Test
    void register_returns400ForInvalidEmail() {
        webTestClient.post().uri("/api/v1/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"not-an-email\",\"password\":\"password123\"}")
                .exchange()
                .expectStatus().isBadRequest();
    }

    @Test
    void register_returns400ForShortPassword() {
        webTestClient.post().uri("/api/v1/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("{\"email\":\"valid@test.com\",\"password\":\"short\"}")
                .exchange()
                .expectStatus().isBadRequest();
    }
}
