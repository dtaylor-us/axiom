package com.specweaver.api.config;

import com.specweaver.api.exception.AgentCommunicationException;
import com.specweaver.api.exception.DocumentProcessingException;
import com.specweaver.api.exception.PackageNotFoundException;
import com.specweaver.api.exception.SessionNotFoundException;
import com.specweaver.api.exception.StorageException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.net.URI;
import java.util.stream.Collectors;

/**
 * Converts application exceptions into ProblemDetail API responses.
 */
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @Value("${spring.servlet.multipart.max-file-size:20MB}")
    private String maxFileSize;

    @ExceptionHandler({NoHandlerFoundException.class, NoResourceFoundException.class})
    public ProblemDetail handleNotFound(Exception ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND, "The requested resource was not found.");
        problem.setTitle("Not Found");
        problem.setType(URI.create("urn:specweaver:not-found"));
        return problem;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        String errors = ex.getBindingResult().getFieldErrors().stream()
                .map(fieldError -> fieldError.getField() + ": " + fieldError.getDefaultMessage())
                .collect(Collectors.joining("; "));
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, errors);
        problem.setTitle("Validation Failed");
        problem.setType(URI.create("urn:specweaver:validation-error"));
        return problem;
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail handleMessageNotReadable(HttpMessageNotReadableException ex) {
        log.warn("Malformed request body: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_REQUEST, "Malformed request body. Check JSON syntax and field values.");
        problem.setTitle("Bad Request");
        problem.setType(URI.create("urn:specweaver:validation-error"));
        return problem;
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ProblemDetail handleMaxUploadSize(MaxUploadSizeExceededException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.PAYLOAD_TOO_LARGE,
                "Maximum upload size is %s. Split large documents before submitting.".formatted(maxFileSize));
        problem.setTitle("File Too Large");
        problem.setType(URI.create("urn:specweaver:file-too-large"));
        return problem;
    }

    /**
     * Returns HTTP 405 when a resource exists but does not support the invoked method.
     */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ProblemDetail handleMethodNotSupported(HttpRequestMethodNotSupportedException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.METHOD_NOT_ALLOWED,
                "HTTP method not supported for this endpoint.");
        problem.setTitle("Method Not Allowed");
        problem.setType(URI.create("urn:specweaver:method-not-allowed"));
        return problem;
    }

    @ExceptionHandler(SessionNotFoundException.class)
    public ProblemDetail handleSessionNotFound(SessionNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Not Found");
        problem.setType(URI.create("urn:specweaver:session-not-found"));
        return problem;
    }

    @ExceptionHandler(PackageNotFoundException.class)
    public ProblemDetail handlePackageNotFound(PackageNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Not Found");
        problem.setType(URI.create("urn:specweaver:package-not-found"));
        return problem;
    }

    @ExceptionHandler(IllegalStateException.class)
    public ProblemDetail handleConflict(RuntimeException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        problem.setTitle("Conflict");
        problem.setType(URI.create("urn:specweaver:conflict"));
        return problem;
    }

    @ExceptionHandler({IllegalArgumentException.class, DocumentProcessingException.class})
    public ProblemDetail handleBadRequest(RuntimeException ex) {
        log.warn("Bad request: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, ex.getMessage());
        problem.setTitle("Bad Request");
        return problem;
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ProblemDetail handleAccessDenied(AccessDeniedException ex) {
        String detail = (ex.getMessage() == null || ex.getMessage().isBlank())
                ? "Forbidden"
                : ex.getMessage();
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.FORBIDDEN, detail);
        problem.setTitle("Forbidden");
        problem.setType(URI.create("urn:specweaver:forbidden"));
        return problem;
    }

    @ExceptionHandler(ResponseStatusException.class)
    public ProblemDetail handleResponseStatus(ResponseStatusException ex) {
        HttpStatus status = HttpStatus.valueOf(ex.getStatusCode().value());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                status, ex.getReason() != null ? ex.getReason() : "No details");
        problem.setTitle(status.getReasonPhrase());
        return problem;
    }

    @ExceptionHandler({AgentCommunicationException.class, WebClientRequestException.class})
    public ProblemDetail handleAgentCommunication(Exception ex) {
        log.warn("Downstream communication failed: {}", ex.getMessage(), ex);
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE, "Downstream service unavailable. Please retry shortly.");
        problem.setTitle("Service Unavailable");
        problem.setType(URI.create("urn:specweaver:downstream-unavailable"));
        return problem;
    }

    @ExceptionHandler(StorageException.class)
    public ProblemDetail handleStorage(StorageException ex) {
        log.warn("Storage operation failed: {}", ex.getMessage(), ex);
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE, "Document storage unavailable. Please retry shortly.");
        problem.setTitle("Service Unavailable");
        problem.setType(URI.create("urn:specweaver:storage-unavailable"));
        return problem;
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleAll(Exception ex) {
        log.error("Unhandled exception", ex);
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred. Please try again.");
        problem.setTitle("Internal Server Error");
        problem.setType(URI.create("urn:specweaver:internal-error"));
        return problem;
    }
}
