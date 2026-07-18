package com.memoria.api.service;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.Project;
import com.memoria.api.dto.CreateAdrRequest;
import com.memoria.api.dto.UpdateAdrRequest;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.ProjectRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AdrServiceTest {

    private ProjectRepository projectRepository;
    private ArchitectureDecisionRepository adrRepository;
    private AdrService adrService;
    private UUID projectId;
    private Project project;

    @BeforeEach
    void setUp() {
        projectRepository = mock(ProjectRepository.class);
        adrRepository = mock(ArchitectureDecisionRepository.class);
        adrService = new AdrService(projectRepository, adrRepository);
        projectId = UUID.randomUUID();
        project = Project.builder().id(projectId).build();
        when(projectRepository.findById(projectId)).thenReturn(Optional.of(project));
        when(adrRepository.save(any(ArchitectureDecision.class))).thenAnswer(invocation -> invocation.getArgument(0));
    }

    @Test
    void createAdr_firstAdrNumberIs1() {
        when(adrRepository.findMaxAdrNumberByProjectId(projectId)).thenReturn(Optional.empty());

        ArchitectureDecision adr = adrService.createAdr(projectId, createRequest());

        assertThat(adr.getAdrNumber()).isEqualTo(1);
    }

    @Test
    void createAdr_incrementsAdrNumber() {
        when(adrRepository.findMaxAdrNumberByProjectId(projectId)).thenReturn(Optional.of(7));

        ArchitectureDecision adr = adrService.createAdr(projectId, createRequest());

        assertThat(adr.getAdrNumber()).isEqualTo(8);
    }

    @Test
    void createAdr_setsStatusProposed() {
        when(adrRepository.findMaxAdrNumberByProjectId(projectId)).thenReturn(Optional.empty());

        ArchitectureDecision adr = adrService.createAdr(projectId, createRequest());

        assertThat(adr.getStatus()).isEqualTo(AdrStatus.PROPOSED);
    }

    @Test
    void updateAdr_updatesAllowedFields() {
        UUID adrId = UUID.randomUUID();
        ArchitectureDecision adr = ArchitectureDecision.builder()
                .id(adrId)
                .project(project)
                .title("Old")
                .status(AdrStatus.PROPOSED)
                .context("Old context")
                .decision("Old decision")
                .build();
        when(adrRepository.findById(adrId)).thenReturn(Optional.of(adr));
        UpdateAdrRequest request = new UpdateAdrRequest(
                "New",
                AdrStatus.ACCEPTED,
                "New context",
                "New decision",
                "Consequences",
                "Alternatives",
                1);

        ArchitectureDecision updated = adrService.updateAdr(projectId, adrId, request);

        assertThat(updated.getTitle()).isEqualTo("New");
        assertThat(updated.getStatus()).isEqualTo(AdrStatus.ACCEPTED);
        assertThat(updated.getContext()).isEqualTo("New context");
        assertThat(updated.getDecision()).isEqualTo("New decision");
        assertThat(updated.getConsequences()).isEqualTo("Consequences");
        assertThat(updated.getAlternativesConsidered()).isEqualTo("Alternatives");
        assertThat(updated.getSupersededByAdrNumber()).isEqualTo(1);
    }

    @Test
    void searchAdrs_filtersByStatusAndText() {
        ArchitectureDecision accepted = adr(UUID.randomUUID(), 1, "PostgreSQL", AdrStatus.ACCEPTED);
        accepted.setContext("Order consistency");
        when(adrRepository.searchByProjectId(projectId, AdrStatus.ACCEPTED, "order"))
                .thenReturn(List.of(accepted));

        List<ArchitectureDecision> adrs = adrService.searchAdrs(projectId, AdrStatus.ACCEPTED, "order");

        assertThat(adrs).containsExactly(accepted);
        verify(adrRepository).searchByProjectId(projectId, AdrStatus.ACCEPTED, "order");
    }

    @Test
    void supersedeAdr_setsStatusAndSupersededByNumber() {
        UUID oldAdrId = UUID.randomUUID();
        UUID newAdrId = UUID.randomUUID();
        ArchitectureDecision oldAdr = adr(oldAdrId, 1, "Old", AdrStatus.ACCEPTED);
        ArchitectureDecision newAdr = adr(newAdrId, 2, "New", AdrStatus.ACCEPTED);
        when(adrRepository.findById(oldAdrId)).thenReturn(Optional.of(oldAdr));
        when(adrRepository.findById(newAdrId)).thenReturn(Optional.of(newAdr));

        ArchitectureDecision superseded = adrService.supersedeAdr(projectId, oldAdrId, newAdrId);

        assertThat(superseded.getStatus()).isEqualTo(AdrStatus.SUPERSEDED);
        assertThat(superseded.getSupersededByAdrNumber()).isEqualTo(2);
    }

    private CreateAdrRequest createRequest() {
        return new CreateAdrRequest("Title", "Context", "Decision", null, null, null, null);
    }

    private ArchitectureDecision adr(UUID id, int adrNumber, String title, AdrStatus status) {
        return ArchitectureDecision.builder()
                .id(id)
                .project(project)
                .adrNumber(adrNumber)
                .title(title)
                .status(status)
                .context("Context")
                .decision("Decision")
                .build();
    }
}
