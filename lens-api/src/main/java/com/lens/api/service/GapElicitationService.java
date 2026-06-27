package com.lens.api.service;

import com.lens.api.client.LensAgentClient;
import com.lens.api.domain.model.GapQuestion;

import java.util.List;
import java.util.UUID;

public class GapElicitationService {

    private final LensAgentClient lensAgentClient;

    public GapElicitationService(LensAgentClient lensAgentClient) {
        this.lensAgentClient = lensAgentClient;
    }

    public List<GapQuestion> generateNextRound(UUID sessionId) {
        return lensAgentClient.generateGapQuestions(sessionId, List.of(), List.of(), List.of(), 1).block();
    }

    public void assessGaps(UUID sessionId) {
        lensAgentClient.assessGapResolution(sessionId, List.of(), List.of(), 1, 5).block();
    }

    public void forceProceed(UUID sessionId) {
        lensAgentClient.forceProceed(sessionId).block();
    }
}
