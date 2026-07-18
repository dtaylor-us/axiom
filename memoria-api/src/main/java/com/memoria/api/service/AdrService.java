package com.memoria.api.service;

import com.memoria.api.domain.model.AdrStatus;
import com.memoria.api.domain.model.ArchitectureDecision;
import com.memoria.api.domain.model.Project;
import com.memoria.api.dto.CreateAdrRequest;
import com.memoria.api.dto.UpdateAdrRequest;
import com.memoria.api.exception.ResourceNotFoundException;
import com.memoria.api.repository.ArchitectureDecisionRepository;
import com.memoria.api.repository.ProjectRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class AdrService {

    private final ProjectRepository projectRepository;
    private final ArchitectureDecisionRepository adrRepository;

    @Transactional
    public ArchitectureDecision createAdr(UUID projectId, CreateAdrRequest req) {
        Project project = requireProject(projectId);
        int adrNumber = adrRepository.findMaxAdrNumberByProjectId(projectId).orElse(0) + 1;
        ArchitectureDecision adr = ArchitectureDecision.builder()
                .project(project)
                .adrNumber(adrNumber)
                .title(req.title())
                .status(AdrStatus.PROPOSED)
                .context(req.context())
                .decision(req.decision())
                .consequences(req.consequences())
                .alternativesConsidered(req.alternativesConsidered())
                .sourcePillar(req.sourcePillar())
                .sourceSessionId(req.sourceSessionId())
                .createdAt(LocalDateTime.now())
                .build();
        return adrRepository.save(adr);
    }

    @Transactional(readOnly = true)
    public List<ArchitectureDecision> listAdrs(UUID projectId) {
        requireProject(projectId);
        return adrRepository.findByProjectIdOrderByAdrNumberAsc(projectId);
    }

    @Transactional(readOnly = true)
    public List<ArchitectureDecision> searchAdrs(UUID projectId, AdrStatus status, String q) {
        requireProject(projectId);
        return adrRepository.findByProjectIdOrderByAdrNumberAsc(projectId).stream()
                .filter(adr -> status == null || adr.getStatus() == status)
                .filter(adr -> matchesText(adr, q))
                .toList();
    }

    @Transactional
    public ArchitectureDecision updateAdr(UUID projectId, UUID adrId, UpdateAdrRequest req) {
        requireProject(projectId);
        ArchitectureDecision adr = adrRepository.findById(adrId)
                .orElseThrow(() -> new ResourceNotFoundException("Architecture decision not found"));
        if (!adr.getProject().getId().equals(projectId)) {
            throw new ResourceNotFoundException("Architecture decision not found");
        }
        if (req.title() != null) {
            adr.setTitle(req.title());
        }
        if (req.status() != null) {
            adr.setStatus(req.status());
        }
        if (req.context() != null) {
            adr.setContext(req.context());
        }
        if (req.decision() != null) {
            adr.setDecision(req.decision());
        }
        if (req.consequences() != null) {
            adr.setConsequences(req.consequences());
        }
        if (req.alternativesConsidered() != null) {
            adr.setAlternativesConsidered(req.alternativesConsidered());
        }
        if (req.supersededByAdrNumber() != null) {
            adr.setSupersededByAdrNumber(req.supersededByAdrNumber());
        }
        return adrRepository.save(adr);
    }

    @Transactional
    public ArchitectureDecision supersedeAdr(UUID projectId, UUID oldAdrId, UUID newAdrId) {
        ArchitectureDecision oldAdr = requireProjectAdr(projectId, oldAdrId);
        ArchitectureDecision newAdr = requireProjectAdr(projectId, newAdrId);
        oldAdr.setStatus(AdrStatus.SUPERSEDED);
        oldAdr.setSupersededByAdrNumber(newAdr.getAdrNumber());
        return adrRepository.save(oldAdr);
    }

    private Project requireProject(UUID projectId) {
        return projectRepository.findById(projectId)
                .orElseThrow(() -> new ResourceNotFoundException("Project not found"));
    }

    private ArchitectureDecision requireProjectAdr(UUID projectId, UUID adrId) {
        requireProject(projectId);
        ArchitectureDecision adr = adrRepository.findById(adrId)
                .orElseThrow(() -> new ResourceNotFoundException("Architecture decision not found"));
        if (!adr.getProject().getId().equals(projectId)) {
            throw new ResourceNotFoundException("Architecture decision not found");
        }
        return adr;
    }

    private boolean matchesText(ArchitectureDecision adr, String query) {
        if (query == null || query.isBlank()) {
            return true;
        }
        String normalized = query.trim().toLowerCase();
        return contains(adr.getTitle(), normalized)
                || contains(adr.getContext(), normalized)
                || contains(adr.getDecision(), normalized)
                || contains(adr.getConsequences(), normalized)
                || contains(adr.getAlternativesConsidered(), normalized);
    }

    private boolean contains(String value, String query) {
        return value != null && value.toLowerCase().contains(query);
    }
}
