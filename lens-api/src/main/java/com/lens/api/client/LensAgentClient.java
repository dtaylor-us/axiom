package com.lens.api.client;

import com.lens.api.domain.model.GapQuestion;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Component
@Slf4j
public class LensAgentClient {

    private final WebClient webClient;

    public LensAgentClient(
        WebClient.Builder webClientBuilder,
        @Value("${lens.agent.base-url:${LENS_AGENT_BASE_URL:http://lens-agent:8086}}") String baseUrl) {
    this.webClient = webClientBuilder.baseUrl(baseUrl).build();
    }

    public Mono<List<GapQuestion>> generateGapQuestions(
        UUID sessionId,
    List<Map<String, Object>> evidence,
    List<Map<String, Object>> previousQuestions,
    List<Map<String, Object>> answers,
        int round
    ) {
    Map<String, Object> request = Map.of(
        "session_id", sessionId.toString(),
        "evidence", evidence,
        "previous_questions", previousQuestions,
        "answers", answers,
        "round", round);

    log.info("lens-agent generateGapQuestions request sessionId={} round={} evidenceCount={}",
        sessionId, round, evidence.size());

    return webClient.post()
        .uri("/gaps/generate")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(request)
        .retrieve()
        .bodyToMono(new ParameterizedTypeReference<List<Map<String, Object>>>() {
        })
        .map(this::mapGapQuestions)
        .doOnNext(response ->
            log.info("lens-agent generateGapQuestions response sessionId={} questions={}",
                sessionId, response.size()))
        .doOnError(error ->
            log.error("lens-agent generateGapQuestions failed sessionId={} round={} error={}",
                sessionId, round, error.getMessage(), error))
        .onErrorMap(error -> new RuntimeException(
            "Failed to generate Lens gap questions for session " + sessionId, error));
    }

    public Mono<Map<String, Object>> assessGapResolution(
        UUID sessionId,
        List<Map<String, Object>> evidence,
        List<Map<String, Object>> questions,
        List<Map<String, Object>> answers,
        int round,
        int maxRounds) {
    Map<String, Object> request = Map.of(
        "session_id", sessionId.toString(),
        "evidence", evidence,
        "questions", questions,
        "answers", answers,
        "round", round,
        "max_rounds", maxRounds);

    log.info("lens-agent assessGapResolution request sessionId={} round={} questions={}",
        sessionId, round, questions.size());

    return webClient.post()
        .uri("/gaps/assess")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(request)
        .retrieve()
        .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {
        })
        .doOnNext(response ->
            log.info("lens-agent assessGapResolution response sessionId={} resolved={} canProceed={}",
                sessionId, response.get("resolved"), response.get("canProceed")))
        .doOnError(error ->
            log.error("lens-agent assessGapResolution failed sessionId={} round={} error={}",
                sessionId, round, error.getMessage(), error))
        .onErrorMap(error -> new RuntimeException(
            "Failed to assess Lens gap resolution for session " + sessionId, error));
    }

    public Mono<Map<String, Object>> runReview(
        UUID sessionId,
        String systemDescription,
        List<Map<String, Object>> evidence,
        List<Map<String, Object>> gapQuestions,
        List<Map<String, Object>> gapAnswers,
        List<String> insufficientInfoGaps) {
    Map<String, Object> request = Map.of(
        "session_id", sessionId.toString(),
        "system_description", systemDescription == null ? "" : systemDescription,
        "evidence", evidence,
        "gap_questions", gapQuestions,
        "gap_answers", gapAnswers,
        "insufficient_info_gaps", insufficientInfoGaps);

    log.info("lens-agent runReview request sessionId={} evidence={} gaps={} answers={} insufficientInfo={}",
        sessionId,
        evidence.size(),
        gapQuestions.size(),
        gapAnswers.size(),
        insufficientInfoGaps.size());

    return webClient.post()
        .uri("/review")
        .contentType(MediaType.APPLICATION_JSON)
        .bodyValue(request)
        .retrieve()
        .bodyToMono(new ParameterizedTypeReference<Map<String, Object>>() {
        })
        .doOnNext(response ->
            log.info("lens-agent runReview response sessionId={} rating={}",
                sessionId, response.get("overallRating")))
        .doOnError(error ->
            log.error("lens-agent runReview failed sessionId={} error={}",
                sessionId, error.getMessage(), error))
        .onErrorMap(error -> new RuntimeException(
            "Failed to run Lens review pipeline for session " + sessionId, error));
    }

    private List<GapQuestion> mapGapQuestions(List<Map<String, Object>> response) {
    return response.stream().map(this::toGapQuestion).toList();
    }

    private GapQuestion toGapQuestion(Map<String, Object> raw) {
    GapQuestion question = new GapQuestion();
    question.setId(UUID.fromString(String.valueOf(raw.get("id"))));
    question.setCategory(Enum.valueOf(com.lens.api.domain.model.GapCategory.class,
        String.valueOf(raw.get("category"))));
    question.setQuestion(String.valueOf(raw.get("question")));
    question.setRationale(raw.get("rationale") == null ? null : String.valueOf(raw.get("rationale")));
    question.setAnswered(false);
    question.setSkipped(false);
    return question;
    }
}
