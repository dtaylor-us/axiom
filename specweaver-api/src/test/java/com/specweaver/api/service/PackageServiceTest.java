package com.specweaver.api.service;

import java.util.Optional;
import java.util.UUID;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.specweaver.api.domain.model.GeneratedPackage;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.exception.PackageNotFoundException;
import com.specweaver.api.repository.GeneratedPackageRepository;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PackageServiceTest {

    @Mock private SessionService sessionService;
    @Mock private GeneratedPackageRepository generatedPackageRepository;
    @Mock private BriefFormatter briefFormatter;

    @Test
    void getBriefText_returnsPersistedBriefWhenAvailable() {
        Session session = session();
        GeneratedPackage generatedPackage = GeneratedPackage.builder()
                .id(UUID.randomUUID())
                .session(session)
                .briefText("cached brief")
                .packageJson("{}")
                .build();

        PackageService packageService = new PackageService(
                sessionService,
                generatedPackageRepository,
                new ObjectMapper(),
                briefFormatter
        );

        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(generatedPackageRepository.findBySessionId(session.getId())).thenReturn(Optional.of(generatedPackage));

        String result = packageService.getBriefText(session.getId(), session.getUserId());

        assertEquals("cached brief", result);
        verify(briefFormatter, never()).format(any(), any());
    }

    @Test
    void getBriefText_generatesAndSavesBriefWhenMissing() {
        Session session = session();
        GeneratedPackage generatedPackage = GeneratedPackage.builder()
                .id(UUID.randomUUID())
                .session(session)
                .packageJson("{\"systemDescription\":\"Payments\",\"requirements\":[]}")
                .build();

        PackageService packageService = new PackageService(
                sessionService,
                generatedPackageRepository,
                new ObjectMapper(),
                briefFormatter
        );

        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(generatedPackageRepository.findBySessionId(session.getId())).thenReturn(Optional.of(generatedPackage));
        when(briefFormatter.format(any(), any())).thenReturn("generated brief");

        String result = packageService.getBriefText(session.getId(), session.getUserId());

        assertEquals("generated brief", result);
        verify(generatedPackageRepository).save(generatedPackage);
    }

    @Test
    void getBriefText_throwsWhenPackageMissing() {
        Session session = session();
        PackageService packageService = new PackageService(
                sessionService,
                generatedPackageRepository,
                new ObjectMapper(),
                briefFormatter
        );

        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(generatedPackageRepository.findBySessionId(session.getId())).thenReturn(Optional.empty());

        assertThrows(PackageNotFoundException.class,
                () -> packageService.getBriefText(session.getId(), session.getUserId()));
    }

    private Session session() {
        return Session.builder()
                .id(UUID.randomUUID())
                .userId(UUID.randomUUID())
                .build();
    }
}
