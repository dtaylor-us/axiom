package com.archon.api.controller;

import com.archon.api.dto.ArchitectureOutputDto;
import com.archon.api.dto.DiagramCollectionDto;
import com.archon.api.dto.DiagramDto;
import com.archon.api.service.ArchitectureOutputService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * REST controller for managing architecture-related endpoints.
 * Handles retrieval of architecture outputs and diagrams for sessions.
 */
@RestController
@RequestMapping("/api/v1/sessions")
@RequiredArgsConstructor
public class ArchitectureController {

        private final ArchitectureOutputService architectureOutputService;

        /**
         * GET /api/v1/sessions/{id}/architecture
         * Returns the latest architecture output for the given conversation.
         *
         * @param id the session ID
         * @param userId the authenticated user ID
         * @return the architecture output DTO or 404 if not found
         */
        @GetMapping("/{id}/architecture")
        public ResponseEntity<ArchitectureOutputDto> getArchitecture(
                        @PathVariable UUID id,
                        @AuthenticationPrincipal String userId) {
                // Retrieve the latest architecture output and return it, or 404 if not found
                return architectureOutputService.getLatest(id)
                                .map(ResponseEntity::ok)
                                .orElse(ResponseEntity.notFound().build());
        }

        /**
         * GET /api/v1/sessions/{id}/diagram
         * Returns the full diagram collection for the given conversation.
         * Includes the new diagrams array alongside backward-compatible flat fields.
         *
         * @param id the session ID
         * @param userId the authenticated user ID
         * @return a DiagramCollectionDto or 404 if no output exists
         */
        @GetMapping("/{id}/diagram")
        public ResponseEntity<DiagramCollectionDto> getDiagram(
                        @PathVariable UUID id,
                        @AuthenticationPrincipal String userId) {
                return architectureOutputService.getDiagramCollection(id)
                                .map(ResponseEntity::ok)
                                .orElse(ResponseEntity.notFound().build());
        }

        /**
         * GET /api/v1/sessions/{id}/diagram/{type}
         * Returns a single diagram by type. Returns 404 when the type is valid
         * but was not generated for this session.
         *
         * @param id the session ID
         * @param type the diagram type identifier (e.g. c4_container, sequence_primary)
         * @param userId the authenticated user ID
         * @return a single DiagramDto or 404
         */
        @GetMapping("/{id}/diagram/{type}")
        public ResponseEntity<DiagramDto> getDiagramByType(
                        @PathVariable UUID id,
                        @PathVariable String type,
                        @AuthenticationPrincipal String userId) {
                return architectureOutputService.getDiagramByType(id, type)
                                .map(ResponseEntity::ok)
                                .orElse(ResponseEntity.notFound().build());
        }

        /**
         * GET /api/v1/sessions/{id}/trade-offs
         * Returns the list of trade-off decisions for the given conversation.
         */
        @GetMapping("/{id}/trade-offs")
        public ResponseEntity<List<Object>> getTradeOffs(
                        @PathVariable UUID id,
                        @AuthenticationPrincipal String userId) {
                return architectureOutputService.getLatest(id)
                                .map(dto -> ResponseEntity.ok(
                                                dto.getTradeOffs() != null ? dto.getTradeOffs() : List.of()))
                                .orElse(ResponseEntity.notFound().build());
        }

        /**
         * GET /api/v1/sessions/{id}/adl
         * Returns the ADL document and rules for the given conversation.
         */
        @GetMapping("/{id}/adl")
        public ResponseEntity<Map<String, Object>> getAdl(
                        @PathVariable UUID id,
                        @AuthenticationPrincipal String userId) {
                return architectureOutputService.getLatest(id)
                                .map(dto -> ResponseEntity.ok(Map.of(
                                                "document", dto.getAdlDocument() != null ? dto.getAdlDocument() : "",
                                                "rules", dto.getAdlRules() != null ? dto.getAdlRules() : List.of()
                                )))
                                .orElse(ResponseEntity.notFound().build());
        }

        /**
         * GET /api/v1/sessions/{id}/weaknesses
         * Returns the weakness report for the given conversation.
         */
        @GetMapping("/{id}/weaknesses")
        public ResponseEntity<Map<String, Object>> getWeaknesses(
                        @PathVariable UUID id,
                        @AuthenticationPrincipal String userId) {
                return architectureOutputService.getLatest(id)
                                .map(dto -> ResponseEntity.ok(Map.of(
                                                "weaknesses", dto.getWeaknesses() != null ? dto.getWeaknesses() : List.of(),
                                                "summary", dto.getWeaknessSummary() != null ? dto.getWeaknessSummary() : ""
                                )))
                                .orElse(ResponseEntity.notFound().build());
        }

        /**
         * GET /api/v1/sessions/{id}/fmea
         * Returns the FMEA risk entries for the given conversation.
         */
        @GetMapping("/{id}/fmea")
        public ResponseEntity<List<Object>> getFmea(
                        @PathVariable UUID id,
                        @AuthenticationPrincipal String userId) {
                return architectureOutputService.getLatest(id)
                                .map(dto -> ResponseEntity.ok(
                                                dto.getFmeaRisks() != null ? dto.getFmeaRisks() : List.of()))
                                .orElse(ResponseEntity.notFound().build());
        }
}
