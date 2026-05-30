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
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Verifies gateway route behavior for Archon requests and auth boundaries.
 */
@SpringBootTest(classes = AxiomApiApplication.class, webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewayRoutingConfigTest {

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
     * Confirms the Archon route strips /api/v1/archon and adds routing headers.
     *
     * @throws Exception when mock server request capture fails
     */
    @Test
    void archonRoute_stripsPrefixAndAddsHeaders() throws Exception {
        archonServer.enqueue(new MockResponse().setResponseCode(200).setBody("ok"));

        webTestClient.get()
                .uri("http://localhost:" + localPort + "/api/v1/archon/actuator/health")
                .header("Authorization", "Bearer " + createToken("user-1", "user@example.com", 300))
                .exchange()
                .expectStatus().isOk();

        RecordedRequest request = archonServer.takeRequest();
        assertEquals("/actuator/health", request.getPath());
        assertEquals("archon", request.getHeader("X-Axiom-Pillar"));
        assertEquals("1", request.getHeader("X-Axiom-Gateway-Version"));
    }

    /**
     * Ensures auth endpoints are handled locally and are not forwarded to pillars.
     */
    @Test
    void authEndpoints_areNotRoutedToPillar() {
        webTestClient.post()
                .uri("http://localhost:" + localPort + "/api/v1/auth/login")
                .exchange()
                .expectStatus().isNotFound();

        assertEquals(0, archonServer.getRequestCount());
    }

    /**
     * Ensures missing JWT fails with 401 before any route forwarding occurs.
     */
    @Test
    void protectedRoute_withoutJwtReturnsUnauthorized() {
        webTestClient.get()
                .uri("http://localhost:" + localPort + "/api/v1/archon/actuator/health")
                .exchange()
                .expectStatus().isUnauthorized();

        assertEquals(0, archonServer.getRequestCount());
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
