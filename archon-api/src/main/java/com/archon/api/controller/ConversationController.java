package com.archon.api.controller;

import com.archon.api.domain.model.Conversation;
import com.archon.api.service.ConversationService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * Conversation lifecycle endpoints that do not execute the pipeline.
 */
@RestController
@RequestMapping("/api/v1/conversations")
@RequiredArgsConstructor
public class ConversationController {

    private final ConversationService conversationService;

    /**
     * Creates a new empty conversation and returns its identifier.
     *
     * <p>The message preview is used only to derive a title. No user message is
     * persisted and no pipeline run is started by this endpoint.</p>
     */
    @PostMapping
    public ResponseEntity<CreateConversationResponse> createConversation(
            @RequestBody @Valid CreateConversationRequest request,
            @AuthenticationPrincipal String userId
    ) {
        Conversation conversation = conversationService.resolveConversation(
                null,
                userId,
                request.messagePreview()
        );
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(new CreateConversationResponse(conversation.getId()));
    }

    public record CreateConversationRequest(
            @NotBlank(message = "messagePreview is required")
            String messagePreview
    ) {
    }

    public record CreateConversationResponse(UUID conversationId) {
    }
}
