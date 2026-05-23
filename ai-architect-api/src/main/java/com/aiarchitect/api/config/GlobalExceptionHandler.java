package com.aiarchitect.api.config;

import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.ratelimiter.RequestNotPermitted;
import com.aiarchitect.api.exception.AgentCommunicationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.net.URI;
import java.util.stream.Collectors;

/**
 * Global exception handler for the application.
 * Converts exceptions into standardized ProblemDetail responses.
 */
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    /**
     * Handles unknown routes and missing static resources.
     *
     * Without this, these exceptions can fall through to the generic handler and
     * be incorrectly reported as 500 Internal Server Error.
     */
    @ExceptionHandler({NoHandlerFoundException.class, NoResourceFoundException.class})
    public ProblemDetail handleNotFound(Exception ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND,
                "The requested resource was not found.");
        pd.setTitle("Not Found");
        pd.setType(URI.create("urn:archon:not-found"));
        return pd;
    }

    /**
     * Handles validation errors from request body binding.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        // Collect all field validation errors into a single string
        String errors = ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
                .collect(Collectors.joining("; "));

        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, errors);
        pd.setTitle("Validation Failed");
        pd.setType(URI.create("urn:archon:validation-error"));
        return pd;
    }

    /**
     * Handles ResponseStatusException with custom HTTP status codes.
     */
    @ExceptionHandler(ResponseStatusException.class)
    public ProblemDetail handleResponseStatus(ResponseStatusException ex) {
        HttpStatus status = HttpStatus.valueOf(ex.getStatusCode().value());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                status,
                ex.getReason() != null ? ex.getReason() : "No details");

        pd.setTitle(status.getReasonPhrase());
        if (status == HttpStatus.NOT_FOUND) {
            pd.setType(URI.create("urn:archon:not-found"));
        }
        return pd;
    }

    /**
     * Handles malformed JSON request bodies.
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail handleMessageNotReadable(HttpMessageNotReadableException ex) {
        log.warn("Malformed request body: {}", ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST,
                "Malformed request body. Check JSON syntax and field values.");
        pd.setTitle("Bad Request");
        pd.setType(URI.create("urn:archon:validation-error"));
        return pd;
    }

    /**
     * Handles IllegalArgumentException for invalid application logic.
     */
    @ExceptionHandler(IllegalArgumentException.class)
    public ProblemDetail handleIllegalArgument(IllegalArgumentException ex) {
        log.warn("Bad request: {}", ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, ex.getMessage());
        pd.setTitle("Bad Request");
        return pd;
    }

    /**
     * Handles circuit breaker open — agent is temporarily unavailable.
     */
    @ExceptionHandler(CallNotPermittedException.class)
    public ProblemDetail handleCircuitBreakerOpen(CallNotPermittedException ex) {
        log.warn("Circuit breaker rejected request: {}", ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE,
                "AI agent temporarily unavailable. Please retry shortly.");
        pd.setTitle("Service Unavailable");
        pd.setType(URI.create("urn:archon:circuit-breaker-open"));
        return pd;
    }

    /**
     * Handles rate limiter rejection — too many concurrent requests.
     */
    @ExceptionHandler(RequestNotPermitted.class)
    public ProblemDetail handleRateLimited(RequestNotPermitted ex) {
        log.warn("Rate limiter rejected request: {}", ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.TOO_MANY_REQUESTS,
                "Too many requests. Please wait before retrying.");
        pd.setTitle("Too Many Requests");
        pd.setType(URI.create("urn:archon:rate-limited"));
        return pd;
    }

    /**
     * Handles agent connectivity failures.
     */
    @ExceptionHandler(WebClientRequestException.class)
    public ProblemDetail handleWebClientRequest(WebClientRequestException ex) {
        log.warn("Downstream request failed: {}", ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE,
                "AI agent unavailable. Please retry shortly.");
        pd.setTitle("Service Unavailable");
        pd.setType(URI.create("urn:archon:agent-unavailable"));
        return pd;
    }

    /**
     * Handles wrapped agent communication failures.
     */
    @ExceptionHandler(AgentCommunicationException.class)
    public ProblemDetail handleAgentCommunication(AgentCommunicationException ex) {
        log.warn("Agent communication failed: {}", ex.getMessage(), ex);
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE,
                "AI agent unavailable. Please retry shortly.");
        pd.setTitle("Service Unavailable");
        pd.setType(URI.create("urn:archon:agent-unavailable"));
        return pd;
    }

    /**
     * Fallback handler for all unhandled exceptions.
     */
    @ExceptionHandler(Exception.class)
    public ProblemDetail handleAll(Exception ex) {
        log.error("Unhandled exception", ex);
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "An unexpected error occurred. Please try again.");
        pd.setTitle("Internal Server Error");
        pd.setType(URI.create("urn:archon:internal-error"));
        return pd;
    }
}
