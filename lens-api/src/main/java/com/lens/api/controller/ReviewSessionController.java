package com.lens.api.controller;

import com.lens.api.domain.model.ReviewSession;
import com.lens.api.service.ReviewSessionService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/lens/sessions")
public class ReviewSessionController {

    private final ReviewSessionService reviewSessionService = new ReviewSessionService();

    public record CreateReviewSessionRequest(@NotBlank String title, String systemDescription) {}

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ReviewSession createSession(@Valid @RequestBody CreateReviewSessionRequest request) {
        return reviewSessionService.createSession(request.title(), request.systemDescription());
    }

    @GetMapping
    public List<ReviewSession> listSessions() {
        return reviewSessionService.listSessions();
    }

    @GetMapping("/{id}")
    public ReviewSession getSession(@PathVariable UUID id) {
        return reviewSessionService.getSession(id);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteSession(@PathVariable UUID id) {
        reviewSessionService.deleteSession(id);
    }
}
