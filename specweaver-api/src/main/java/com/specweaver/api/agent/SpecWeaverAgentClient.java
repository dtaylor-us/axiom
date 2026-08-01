package com.specweaver.api.agent;

import com.specweaver.api.config.AgentClientConfig;
import com.specweaver.api.exception.AgentCommunicationException;
import io.netty.channel.ChannelOption;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;

/**
 * HTTP client for specweaver-agent extraction pipeline calls.
 *
 * <p>Uses a Netty {@link HttpClient} with explicit response and connection timeouts so that
 * the Reactor {@code .timeout()} operator and the underlying transport timeout are both
 * aligned with {@code agent.timeout-seconds}. Without the Netty-level response timeout the
 * underlying TCP connection can stall silently even after the Reactor timeout fires.
 *
 * @author OpenAI
 */
@Component
@EnableConfigurationProperties(AgentClientConfig.class)
@Slf4j
public class SpecWeaverAgentClient {

    /** Connection-establishment timeout in milliseconds. */
    private static final int CONNECT_TIMEOUT_MS = 10_000;

    private final WebClient webClient;
    private final AgentClientConfig config;

    public SpecWeaverAgentClient(AgentClientConfig config) {
        this.config = config;
        Duration responseTimeout = Duration.ofSeconds(config.getTimeoutSeconds());
        HttpClient httpClient = HttpClient.create()
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, CONNECT_TIMEOUT_MS)
                .responseTimeout(responseTimeout);
        this.webClient = WebClient.builder()
                .baseUrl(config.getBaseUrl())
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .build();
    }

    /**
     * Calls specweaver-agent to extract an ArchInputPackage.
     *
     * @param request extraction request
     * @return agent response
     */
    public AgentExtractionResponse extract(AgentExtractionRequest request) {
        log.info(
                "Calling specweaver-agent sessionId={} timeoutSeconds={}",
                request.sessionId(),
                config.getTimeoutSeconds());
        try {
            return webClient.post()
                    .uri("/agent/extract")
                    .bodyValue(request)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, response ->
                            response.bodyToMono(String.class).map(body ->
                                    new AgentCommunicationException(
                                            "Agent error " + response.statusCode() + ": " + body)))
                    .bodyToMono(AgentExtractionResponse.class)
                    // Belt-and-suspenders Reactor timeout on top of the Netty response timeout.
                    .timeout(Duration.ofSeconds(config.getTimeoutSeconds()))
                    .block();
        } catch (RuntimeException e) {
            log.warn("SpecWeaver agent extraction failed sessionId={}", request.sessionId(), e);
            throw new AgentCommunicationException("SpecWeaver agent extraction failed", e);
        }
    }
}
