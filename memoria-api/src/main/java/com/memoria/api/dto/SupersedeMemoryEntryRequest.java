package com.memoria.api.dto;

import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record SupersedeMemoryEntryRequest(@NotNull UUID newEntryId) {
}
