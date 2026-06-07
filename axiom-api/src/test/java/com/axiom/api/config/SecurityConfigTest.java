package com.axiom.api.config;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import com.axiom.api.AxiomApiApplication;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Verifies reactive security rules for protected and public gateway endpoints.
 */
@SpringBootTest(
        classes = AxiomApiApplication.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "test.context=security")
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class SecurityConfigTest {

    private static final String JWT_SECRET = "abcdefghijklmnopqrstuvwxyz123456";

    private static MockWebServer archonServer;

    @LocalServerPort
    private int localPort;

    @Autowired
    private WebTestClient webTestClient;

    @BeforeAll
    static void startServer() throws IOException {
        archonServer = new MockWebServer();
        archonServer.start();
    }

    @AfterAll
    static void stopServer() throws IOException {
        archonServer.shutdown();
    }

    @DynamicPropertySource
    static void registerProperties(DynamicPropertyRegistry registry) {
        registry.add("ARCHON_API_BASE_URL", () -> archonServer.url("/").toString());
        registry.add("JWT_SECRET", () -> JWT_SECRET);
    }

    /**
     * Valid JWTs must authenticate protected routes.
     */
    @Test
    void validJwtOnProtectedEndpointReturns200() throws InterruptedException {
        archonServer.enqueue(new MockResponse().setResponseCode(200).setBody("ok"));

        webTestClient.get()
                .uri("http://localhost:" + localPort + "/api/v1/archon/actuator/health")
                .header("Authorization", "Bearer " + createToken("user-1", "user@example.com", 300))
                .exchange()
                .expectStatus().isOk();

        assertEquals(1, archonServer.getRequestCount());
    }

    /**
     * Missing JWTs must be rejected for protected routes.
     */
    @Test
    void missingJwtOnProtectedEndpointReturns401() {
        webTestClient.get()
                .uri("http://localhost:" + localPort + "/api/v1/archon/actuator/health")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    /**
     * Expired JWTs must be rejected for protected routes.
     */
    @Test
    void expiredJwtOnProtectedEndpointReturns401() {
        webTestClient.get()
                .uri("http://localhost:" + localPort + "/api/v1/archon/actuator/health")
                .header("Authorization", "Bearer " + createToken("user-1", "user@example.com", -60))
                .exchange()
                .expectStatus().isUnauthorized();
    }

    /**
     * Malformed JWTs must be rejected for protected routes.
     */
    @Test
    void malformedJwtOnProtectedEndpointReturns401() {
        webTestClient.get()
                .uri("http://localhost:" + localPort + "/api/v1/archon/actuator/health")
                .header("Authorization", "Bearer malformed.token.value")
                .exchange()
                .expectStatus().isUnauthorized();
    }

    /**
     * Auth endpoints must route without a gateway JWT challenge.
     */
    @Test
    void authEndpointsAreAccessibleWithoutJwt() throws InterruptedException {
        archonServer.enqueue(new MockResponse().setResponseCode(401));

        webTestClient.post()
                .uri("http://localhost:" + localPort + "/api/v1/auth/login")
                .header("Content-Type", "application/json")
                .bodyValue("{\"email\":\"test@test.com\",\"password\":\"wrong\"}")
                .exchange()
                .expectStatus().isUnauthorized();

        RecordedRequest forwardedRequest = archonServer.takeRequest();
        assertEquals("/api/v1/auth/login", forwardedRequest.getPath());
    }

    /**
     * Auth login must be forwarded to archon-api without path rewriting.
     */
    @Test
    void authLoginRoutesToArchonApi() throws InterruptedException {
        archonServer.enqueue(new MockResponse()
                .setResponseCode(200)
                .addHeader("Content-Type", "application/json")
                .setBody("{\"token\":\"gateway-token\",\"email\":\"user@example.com\"}"));

        String requestBody = "{\"email\":\"user@example.com\",\"password\":\"secret\"}";

        webTestClient.post()
                .uri("http://localhost:" + localPort + "/api/v1/auth/login")
                .header("Content-Type", "application/json")
                .bodyValue(requestBody)
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.token").isEqualTo("gateway-token");

        RecordedRequest forwardedRequest = archonServer.takeRequest();
        assertEquals("POST", forwardedRequest.getMethod());
        assertEquals("/api/v1/auth/login", forwardedRequest.getPath());
        assertEquals(requestBody, forwardedRequest.getBody().readString(StandardCharsets.UTF_8));
    }

    /**
     * Actuator health endpoint is public and bypasses JWT checks.
     */
    @Test
    void actuatorHealthBypassesJwtCheck() {
        webTestClient.get()
                .uri("http://localhost:" + localPort + "/actuator/health")
                .exchange()
                .expectStatus().isOk();
    }

    private static String createToken(String subject, String email, long validForSeconds) {
        long now = Instant.now().getEpochSecond();
        long expiration = now + validForSeconds;

        String headerJson = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payloadJson = "{\"sub\":\"" + subject + "\",\"email\":\"" + email
                + "\",\"exp\":" + expiration + "}";

        String encodedHeader = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(headerJson.getBytes(StandardCharsets.UTF_8));
        String encodedPayload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(payloadJson.getBytes(StandardCharsets.UTF_8));
        String signingInput = encodedHeader + "." + encodedPayload;

        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(JWT_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            String signature = Base64.getUrlEncoder().withoutPadding().encodeToString(
                    mac.doFinal(signingInput.getBytes(StandardCharsets.UTF_8)));
            return signingInput + "." + signature;
        } catch (Exception ex) {
            throw new IllegalStateException("Failed to build JWT for tests", ex);
        }
    }
}
