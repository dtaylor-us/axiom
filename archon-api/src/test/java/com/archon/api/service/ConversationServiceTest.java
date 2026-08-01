package com.archon.api.service;

import com.archon.api.domain.model.*;
import com.archon.api.domain.repository.ConversationRepository;
import com.archon.api.domain.repository.MessageRepository;
import com.archon.api.dto.MessageDto;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ConversationServiceTest {

    @Mock private ConversationRepository conversationRepo;
    @Mock private MessageRepository messageRepo;
    @InjectMocks private ConversationService conversationService;

    @Test
    void resolveConversation_createsNewWhenIdIsNull() {
        Conversation saved = Conversation.builder()
                .id(UUID.randomUUID()).userId("user1").title("hello").build();
        when(conversationRepo.save(any())).thenReturn(saved);

        Conversation result = conversationService.resolveConversation(
                null, "user1", "hello world");

        assertNotNull(result.getId());
        verify(conversationRepo).save(any(Conversation.class));
        verify(conversationRepo, never()).findByIdAndUserIdIn(any(), any());
    }

    @Test
    void resolveConversation_throwsNotFoundForUnknownId() {
        UUID unknown = UUID.randomUUID();
        when(conversationRepo.findByIdAndUserIdIn(eq(unknown), any()))
                .thenReturn(Optional.empty());

        ResponseStatusException ex = assertThrows(ResponseStatusException.class, () ->
                conversationService.resolveConversation(unknown, "user1", "msg"));
        assertEquals(404, ex.getStatusCode().value());
    }

    @Test
    void resolveConversation_returnsExistingWhenFound() {
        UUID existing = UUID.randomUUID();
        Conversation conv = Conversation.builder()
                .id(existing).userId("user1").title("test").build();
        when(conversationRepo.findByIdAndUserIdIn(eq(existing), any()))
                .thenReturn(Optional.of(conv));

        Conversation result = conversationService.resolveConversation(
                existing, "user1", "msg");

        assertEquals(existing, result.getId());
        verify(conversationRepo, never()).save(any());
    }

    @Test
    void resolveConversation_truncatesTitleToSixtyChars() {
        String longMessage = "A".repeat(100);
        when(conversationRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

        conversationService.resolveConversation(null, "user1", longMessage);

        ArgumentCaptor<Conversation> captor =
                ArgumentCaptor.forClass(Conversation.class);
        verify(conversationRepo).save(captor.capture());
        assertTrue(captor.getValue().getTitle().endsWith("..."));
        assertEquals(63, captor.getValue().getTitle().length());
    }

    @Test
    void getRecentMessages_returnsAtMostRequestedLimit() {
        UUID convId = UUID.randomUUID();
        Message m1 = Message.builder().id(UUID.randomUUID())
                .role(MessageRole.USER).content("hi")
                .createdAt(Instant.now()).build();
        when(messageRepo.findRecentByConversationId(eq(convId), any(PageRequest.class)))
                .thenReturn(List.of(m1));

        List<MessageDto> result = conversationService.getRecentMessages(convId, 5);

        assertEquals(1, result.size());
        assertEquals("hi", result.get(0).getContent());
        verify(messageRepo).findRecentByConversationId(convId, PageRequest.of(0, 5));
    }

    @Test
    void saveMessage_persistsRoleAndContent() {
        Conversation conv = Conversation.builder()
                .id(UUID.randomUUID()).userId("user1").title("t").build();
        when(messageRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

        Message saved = conversationService.saveMessage(
                conv, MessageRole.USER, "hello", null);

        assertEquals(MessageRole.USER, saved.getRole());
        assertEquals("hello", saved.getContent());
        assertNull(saved.getStructuredOutput());
        verify(messageRepo).save(any(Message.class));
    }

    @Test
    void saveMessage_persistsStructuredOutput() {
        Conversation conv = Conversation.builder()
                .id(UUID.randomUUID()).userId("user1").title("t").build();
        when(messageRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

        Message saved = conversationService.saveMessage(
                conv, MessageRole.ASSISTANT, "response", "{\"key\":\"val\"}");

        assertEquals("{\"key\":\"val\"}", saved.getStructuredOutput());
    }
}
