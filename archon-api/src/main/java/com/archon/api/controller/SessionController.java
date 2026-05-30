package com.archon.api.controller;

import com.archon.api.dto.MessageDto;
import com.archon.api.dto.SessionDto;
import com.archon.api.service.ConversationService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.UUID;

/**
 * REST controller for managing user sessions and conversation messages.
 */
@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final ConversationService conversationService;

    /**
     * Retrieves all sessions (conversations) for the authenticated user.
     */
    @GetMapping
    public List<SessionDto> listSessions(@AuthenticationPrincipal String userId) {
        return conversationService.listSessions(userId);
    }

    /**
     * Retrieves recent messages for a specific session.
     *
     * @param id the session UUID
     * @param userId the authenticated user ID
     * @return a list of recent messages (up to 100)
     */
    @GetMapping("/{id}/messages")
    public List<MessageDto> getMessages(
            @PathVariable UUID id,
            @AuthenticationPrincipal String userId) {
        return conversationService.getRecentMessages(id, userId, 100);
    }
}
