package com.memoria.api.dto;

import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record SupersedeAdrRequest(@NotNull UUID newAdrId) {
}
