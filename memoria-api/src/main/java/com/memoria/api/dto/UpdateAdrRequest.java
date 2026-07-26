package com.memoria.api.dto;

import com.memoria.api.domain.model.AdrStatus;

public record UpdateAdrRequest(
        String title,
        AdrStatus status,
        String context,
        String decision,
        String consequences,
        String alternativesConsidered,
        Integer supersededByAdrNumber) {
}
