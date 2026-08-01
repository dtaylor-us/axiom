package com.axiom.api.dto;

import java.util.Map;

/**
 * API contract for aggregated platform health details.
 *
 * @param status overall gateway status
 * @param components per-pillar health map
 */
public record GatewayHealthDto(String status, Map<String, PillarStatusDto> components) {
}
