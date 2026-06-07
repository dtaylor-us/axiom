package com.specweaver.api.service;

import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionStatus;
import com.specweaver.api.dto.request.CreateSessionRequest;
import com.specweaver.api.dto.request.UpdateSessionRequest;
import com.specweaver.api.exception.SessionNotFoundException;
import com.specweaver.api.repository.SessionRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.access.AccessDeniedException;

import java.util.Optional;
import java.util.UUID;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SessionServiceTest {

    @Mock private SessionRepository sessionRepository;
    @InjectMocks private SessionService sessionService;

    @Test
    void createSession_setsUserIdFromAuthenticatedUser() {
        UUID userId = UUID.randomUUID();
        when(sessionRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        sessionService.createSession(new CreateSessionRequest("New system"), userId);

        ArgumentCaptor<Session> captor = ArgumentCaptor.forClass(Session.class);
        verify(sessionRepository).save(captor.capture());
        assertEquals(userId, captor.getValue().getUserId());
    }

    @Test
    void createSession_setsStatusActive() {
        when(sessionRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = sessionService.createSession(new CreateSessionRequest("New system"), UUID.randomUUID());

        assertEquals(SessionStatus.ACTIVE, response.status());
    }

    @Test
    void createSession_normalizesBlankTitleToNull() {
        when(sessionRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = sessionService.createSession(new CreateSessionRequest("   \n  "), UUID.randomUUID());

        assertNull(response.title());
    }

    @Test
    void updateSessionTitle_updatesOwnedSessionTitle() {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        Session session = Session.builder().id(sessionId).userId(userId).status(SessionStatus.ACTIVE).build();
        when(sessionRepository.findByIdAndStatusNot(sessionId, SessionStatus.DELETED))
                .thenReturn(Optional.of(session));
        when(sessionRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = sessionService.updateSessionTitle(sessionId, userId, new UpdateSessionRequest("  Discovery  "));

        assertEquals("Discovery", response.title());
    }

    @Test
    void updateSessionTitle_convertsBlankTitleToNull() {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        Session session = Session.builder().id(sessionId).userId(userId).status(SessionStatus.ACTIVE).build();
        when(sessionRepository.findByIdAndStatusNot(sessionId, SessionStatus.DELETED))
                .thenReturn(Optional.of(session));
        when(sessionRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        var response = sessionService.updateSessionTitle(sessionId, userId, new UpdateSessionRequest("   "));

        assertNull(response.title());
    }

    @Test
    void getSession_throwsSessionNotFoundExceptionForUnknownId() {
        UUID sessionId = UUID.randomUUID();
        when(sessionRepository.findByIdAndStatusNot(sessionId, SessionStatus.DELETED))
                .thenReturn(Optional.empty());

        assertThrows(SessionNotFoundException.class,
                () -> sessionService.getSession(sessionId, UUID.randomUUID()));
    }

    @Test
    void getSession_throwsAccessDeniedExceptionForWrongUser() {
        UUID sessionId = UUID.randomUUID();
        Session session = Session.builder().id(sessionId).userId(UUID.randomUUID()).build();
        when(sessionRepository.findByIdAndStatusNot(sessionId, SessionStatus.DELETED))
                .thenReturn(Optional.of(session));

        assertThrows(AccessDeniedException.class,
                () -> sessionService.getSession(sessionId, UUID.randomUUID()));
    }

    @Test
    void deleteSession_setsStatusDeleted() {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();
        Session session = Session.builder().id(sessionId).userId(userId).status(SessionStatus.ACTIVE).build();
        when(sessionRepository.findByIdAndStatusNot(sessionId, SessionStatus.DELETED))
                .thenReturn(Optional.of(session));

        sessionService.deleteSession(sessionId, userId);

        assertEquals(SessionStatus.DELETED, session.getStatus());
        verify(sessionRepository).save(session);
    }

    @Test
    void listSessions_returnsRepositorySessions() {
        UUID userId = UUID.randomUUID();
        Session session = Session.builder().id(UUID.randomUUID()).userId(userId).build();
        when(sessionRepository.findByUserIdAndStatusNotOrderByCreatedAtDesc(userId, SessionStatus.DELETED))
                .thenReturn(List.of(session));

        var responses = sessionService.listSessions(userId);

        assertEquals(1, responses.size());
        assertEquals(session.getId(), responses.getFirst().id());
    }
}
