package com.specweaver.api.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.specweaver.api.agent.AgentExtractionResponse;
import com.specweaver.api.agent.SpecWeaverAgentClient;
import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.DocumentType;
import com.specweaver.api.domain.model.GeneratedPackage;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionDocument;
import com.specweaver.api.domain.model.SessionStatus;
import com.specweaver.api.exception.PackageNotFoundException;
import com.specweaver.api.repository.GeneratedPackageRepository;
import com.specweaver.api.repository.SessionDocumentRepository;
import com.specweaver.api.repository.SessionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.ArrayList;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PackageGenerationServiceTest {

    @Mock private SessionService sessionService;
    @Mock private SessionRepository sessionRepository;
    @Mock private SessionDocumentRepository documentRepository;
    @Mock private GeneratedPackageRepository packageRepository;
    @Mock private SpecWeaverAgentClient agentClient;
    @Mock private BriefFormatter briefFormatter;
    @Mock private MemoriaNotificationClient memoriaNotificationClient;
    private PackageGenerationService packageGenerationService;

    @BeforeEach
    void setUp() {
        packageGenerationService = new PackageGenerationService(
                sessionService,
                sessionRepository,
                documentRepository,
                packageRepository,
                agentClient,
                new ObjectMapper(),
                new ReadinessScoreService(),
                briefFormatter,
                memoriaNotificationClient);
    }

    @Test
    void generatePackage_setsSessionStatusToProcessing() {
        Session session = session();
        List<SessionStatus> savedStatuses = new ArrayList<>();
        when(sessionRepository.save(any())).thenAnswer(invocation -> {
            Session saved = invocation.getArgument(0);
            savedStatuses.add(saved.getStatus());
            return saved;
        });
        stubSuccessfulGeneration(session);

        packageGenerationService.generatePackage(session.getId(), session.getUserId());

        assertEquals(SessionStatus.PROCESSING, savedStatuses.getFirst());
    }

    @Test
    void generatePackage_callsSpecWeaverAgentClientExtract() {
        Session session = session();
        stubSuccessfulGeneration(session);

        packageGenerationService.generatePackage(session.getId(), session.getUserId());

        verify(agentClient).extract(any());
    }

    @Test
    void generatePackage_setsSessionStatusToPackageReady() {
        Session session = session();
        stubSuccessfulGeneration(session);

        packageGenerationService.generatePackage(session.getId(), session.getUserId());

        assertEquals(SessionStatus.PACKAGE_READY, session.getStatus());
    }

    @Test
    void generatePackage_storesArchInputPackageJson() {
        Session session = session();
        stubSuccessfulGeneration(session);

        var response = packageGenerationService.generatePackage(session.getId(), session.getUserId());

        assertEquals(List.of(), response.requirements());
    }

    @Test
    void generatePackage_mapsMetricsFromAgentPackage() {
        Session session = session();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findBySessionIdAndStatusOrderByCreatedAtAsc(session.getId(), DocumentStatus.EXTRACTED))
                .thenReturn(List.of(document(session)));
        when(agentClient.extract(any())).thenReturn(new AgentExtractionResponse(
                session.getId().toString(),
                """
                        {"requirements":[],"gaps":[{"severity":"critical"}],"conflicts":[],
                        "totalRequirements":3,"highConfidenceCount":2,"inferredCount":1,
                        "duplicateCount":1,"gapCount":1,"conflictCount":0}
                        """,
                true,
                null));
        when(packageRepository.findBySessionId(session.getId())).thenReturn(Optional.empty());
        when(packageRepository.save(any())).thenAnswer(invocation -> {
            GeneratedPackage generatedPackage = invocation.getArgument(0);
            generatedPackage.setId(UUID.randomUUID());
            return generatedPackage;
        });

        var response = packageGenerationService.generatePackage(session.getId(), session.getUserId());

        assertEquals(3, response.totalRequirements());
        assertEquals(2, response.highConfidenceCount());
        assertEquals(1, response.inferredCount());
        assertEquals(1, response.duplicateCount());
        assertEquals(1, response.gapCount());
        assertEquals(new java.math.BigDecimal("0.85"), response.readinessScore());
    }

    @Test
    void generatePackage_usesGapAndConflictArraySizesWhenCountsAreMissing() {
        Session session = session();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findBySessionIdAndStatusOrderByCreatedAtAsc(session.getId(), DocumentStatus.EXTRACTED))
                .thenReturn(List.of(document(session)));
        when(agentClient.extract(any())).thenReturn(new AgentExtractionResponse(
                session.getId().toString(),
                """
                        {"requirements":[{"id":"REQ-1"}],
                        "gaps":[{"severity":"critical"},{"severity":"high"}],
                        "conflicts":[{"description":"A"}],
                        "totalRequirements":2,"highConfidenceCount":1,"inferredCount":0,
                        "duplicateCount":0,"gapCount":0,"conflictCount":0}
                        """,
                true,
                null));
        when(packageRepository.findBySessionId(session.getId())).thenReturn(Optional.empty());
        when(packageRepository.save(any())).thenAnswer(invocation -> {
            GeneratedPackage generatedPackage = invocation.getArgument(0);
            generatedPackage.setId(UUID.randomUUID());
            return generatedPackage;
        });

        var response = packageGenerationService.generatePackage(session.getId(), session.getUserId());

        assertEquals(2, response.gapCount());
        assertEquals(1, response.conflictCount());
        assertEquals(new java.math.BigDecimal("0.72"), response.readinessScore());
        assertEquals("Mostly ready — minor gaps", response.readinessLabel());
    }

    @Test
    void generatePackage_setsStatusActiveOnAgentFailure() {
        Session session = session();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findBySessionIdAndStatusOrderByCreatedAtAsc(session.getId(), DocumentStatus.EXTRACTED))
                .thenReturn(List.of(document(session)));
        when(agentClient.extract(any())).thenThrow(new RuntimeException("down"));

        assertThrows(RuntimeException.class,
                () -> packageGenerationService.generatePackage(session.getId(), session.getUserId()));

        assertEquals(SessionStatus.ACTIVE, session.getStatus());
    }

    @Test
    void generatePackage_throwsWhenNoExtractedDocs() {
        Session session = session();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findBySessionIdAndStatusOrderByCreatedAtAsc(session.getId(), DocumentStatus.EXTRACTED))
                .thenReturn(List.of());

        assertThrows(IllegalArgumentException.class,
                () -> packageGenerationService.generatePackage(session.getId(), session.getUserId()));
    }

    @Test
    void getPackage_returnsPackageWhenAvailable() {
        Session session = session();
        GeneratedPackage generatedPackage = GeneratedPackage.builder()
                .id(UUID.randomUUID())
                .session(session)
                .packageJson("{\"requirements\":[]}")
                .build();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(packageRepository.findBySessionId(session.getId())).thenReturn(Optional.of(generatedPackage));

        var response = packageGenerationService.getPackage(session.getId(), session.getUserId());

        assertEquals(generatedPackage.getId(), response.packageId());
    }

    @Test
    void getPackage_throwsPackageNotFoundExceptionWhenMissing() {
        Session session = session();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(packageRepository.findBySessionId(session.getId())).thenReturn(Optional.empty());

        assertThrows(PackageNotFoundException.class,
                () -> packageGenerationService.getPackage(session.getId(), session.getUserId()));
    }

    private void stubSuccessfulGeneration(Session session) {
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findBySessionIdAndStatusOrderByCreatedAtAsc(session.getId(), DocumentStatus.EXTRACTED))
                .thenReturn(List.of(document(session)));
        when(agentClient.extract(any())).thenReturn(new AgentExtractionResponse(
                session.getId().toString(), "{\"requirements\":[]}", true, null));
        when(briefFormatter.format(any(), any())).thenReturn("brief");
        when(packageRepository.findBySessionId(session.getId())).thenReturn(Optional.empty());
        when(packageRepository.save(any())).thenAnswer(invocation -> {
            GeneratedPackage generatedPackage = invocation.getArgument(0);
            generatedPackage.setId(UUID.randomUUID());
            return generatedPackage;
        });
    }

    private Session session() {
        return Session.builder()
                .id(UUID.randomUUID())
                .userId(UUID.randomUUID())
                .status(SessionStatus.ACTIVE)
                .build();
    }

    private SessionDocument document(Session session) {
        return SessionDocument.builder()
                .id(UUID.randomUUID())
                .session(session)
                .documentType(DocumentType.PLAIN_TEXT)
                .extractedText("requirements")
                .status(DocumentStatus.EXTRACTED)
                .build();
    }
}
