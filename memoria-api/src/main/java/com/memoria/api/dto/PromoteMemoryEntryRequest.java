package com.memoria.api.dto;

import jakarta.validation.constraints.NotBlank;

public record PromoteMemoryEntryRequest(
        String title,
        @NotBlank String context,
        @NotBlank String decision,
        String consequences,
        String alternativesConsidered) {
}
