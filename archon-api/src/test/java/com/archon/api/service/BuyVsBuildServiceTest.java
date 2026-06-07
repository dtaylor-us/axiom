package com.archon.api.service;

import com.archon.api.domain.model.BuyVsBuildDecision;
import com.archon.api.domain.model.Conversation;
import com.archon.api.domain.repository.BuyVsBuildRepository;
import com.archon.api.dto.BuyVsBuildSummaryDto;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Captor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class BuyVsBuildServiceTest {

    @Mock
    private BuyVsBuildRepository repository;

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Captor
    private ArgumentCaptor<BuyVsBuildDecision> entityCaptor;

    @Test
    void saveDecisions_persistsOneRowPerDecision() {
        Conversation conv = Conversation.builder().id(UUID.randomUUID()).userId("u").title("t").build();
        List<Map<String, Object>> decisions = List.of(
                Map.ofEntries(
                        Map.entry("component_name", "Identity"),
                        Map.entry("recommendation", "adopt"),
                        Map.entry("rationale", "Adopt Keycloak for SSO; building OAuth/SAML is non-core and risky."),
                        Map.entry("alternatives_considered", List.of("Keycloak", "Auth0")),
                        Map.entry("recommended_solution", "Keycloak 24.x"),
                        Map.entry("estimated_build_cost", "free, ~$200/month infra"),
                        Map.entry("vendor_lock_in_risk", "low"),
                        Map.entry("integration_effort", "medium"),
                        Map.entry("conflicts_with_user_preference", false),
                        Map.entry("conflict_explanation", ""),
                        Map.entry("is_core_differentiator", false)
                ),
                Map.ofEntries(
                        Map.entry("component_name", "Payments"),
                        Map.entry("recommendation", "buy"),
                        Map.entry("rationale", "Buy Stripe rather than building payment processing; PCI scope and fraud tooling are prohibitive."),
                        Map.entry("alternatives_considered", List.of("Stripe", "Adyen")),
                        Map.entry("recommended_solution", "Stripe"),
                        Map.entry("estimated_build_cost", "~$500/month"),
                        Map.entry("vendor_lock_in_risk", "high"),
                        Map.entry("integration_effort", "low"),
                        Map.entry("conflicts_with_user_preference", true),
                        Map.entry("conflict_explanation", "User wants in-house but payment processing should not be built."),
                        Map.entry("is_core_differentiator", false)
                )
        );

        BuyVsBuildService real = new BuyVsBuildService(repository, objectMapper);

        real.saveDecisions(conv, decisions);

        verify(repository, times(2)).save(entityCaptor.capture());
        assertThat(entityCaptor.getAllValues()).hasSize(2);
        assertThat(entityCaptor.getAllValues().getFirst().getConversationId())
                .isEqualTo(conv.getId());
    }

    @Test
    void saveDecisions_handlesEmptyListWithoutError() {
        Conversation conv = Conversation.builder().id(UUID.randomUUID()).userId("u").title("t").build();
        BuyVsBuildService real = new BuyVsBuildService(repository, objectMapper);

        real.saveDecisions(conv, List.of());

        verify(repository, never()).save(any());
    }

    @Test
    void getSummary_returnsCorrectBuildBuyAdoptCounts() {
        UUID conversationId = UUID.randomUUID();
        when(repository.findByConversationId(conversationId)).thenReturn(List.of(
                BuyVsBuildDecision.builder().id(UUID.randomUUID()).conversationId(conversationId)
                        .componentName("Core").recommendation("build").rationale("x")
                        .vendorLockInRisk("low").integrationEffort("low").build(),
                BuyVsBuildDecision.builder().id(UUID.randomUUID()).conversationId(conversationId)
                        .componentName("Email").recommendation("buy").rationale("x")
                        .vendorLockInRisk("high").integrationEffort("low").build(),
                BuyVsBuildDecision.builder().id(UUID.randomUUID()).conversationId(conversationId)
                        .componentName("Search").recommendation("adopt").rationale("x")
                        .vendorLockInRisk("low").integrationEffort("medium").build()
        ));

        BuyVsBuildService service = new BuyVsBuildService(repository, objectMapper);
        BuyVsBuildSummaryDto summary = service.getSummary(conversationId);

        assertThat(summary.totalDecisions()).isEqualTo(3);
        assertThat(summary.buildCount()).isEqualTo(1);
        assertThat(summary.buyCount()).isEqualTo(1);
        assertThat(summary.adoptCount()).isEqualTo(1);
    }

    @Test
    void getByRecommendation_filtersCorrectly() {
        UUID conversationId = UUID.randomUUID();
        when(repository.findByConversationIdAndRecommendation(conversationId, "build")).thenReturn(List.of(
                BuyVsBuildDecision.builder().id(UUID.randomUUID()).conversationId(conversationId)
                        .componentName("Core").recommendation("build").rationale("x")
                        .vendorLockInRisk("low").integrationEffort("low").build()
        ));

        BuyVsBuildService service = new BuyVsBuildService(repository, objectMapper);
        var items = service.getByRecommendation(conversationId, "build");

        assertThat(items).hasSize(1);
        assertThat(items.getFirst().getRecommendation()).isEqualTo("build");
    }
}

