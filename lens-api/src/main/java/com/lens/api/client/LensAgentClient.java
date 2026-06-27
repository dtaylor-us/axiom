package com.lens.api.client;

import com.lens.api.domain.model.GapQuestion;
import com.lens.api.domain.model.ReviewSession;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.UUID;

public class LensAgentClient {

    private final WebClient webClient;

    public LensAgentClient(WebClient webClient) {
        this.webClient = webClient;
    }

    public Mono<List<GapQuestion>> generateGapQuestions(
        UUID sessionId,
        List<?> evidence,
        List<?> previousQuestions,
        List<?> answers,
        int round
    ) {
        return Mono.just(List.of());
    }

    public Mono<Object> assessGapResolution(UUID sessionId, List<?> questions, List<?> answers, int round, int maxRounds) {
        return Mono.just(new Object());
    }

    public Mono<ReviewSession> forceProceed(UUID sessionId) {
        return Mono.empty();
    }

    public Flux<String> streamReviewPipeline(
        UUID sessionId,
        List<?> evidence,
        List<?> allQuestions,
        List<?> allAnswers,
        List<?> insufficientInfoGaps
    ) {
        return Flux.empty();
    }
}
