package com.memoria.api.controller;

import com.memoria.api.domain.model.MemoryStatus;
import com.memoria.api.dto.CreateMemoryEntryRequest;
import com.memoria.api.dto.MemoryEntryResponse;
import com.memoria.api.dto.SupersedeMemoryEntryRequest;
import com.memoria.api.dto.UpdateMemoryEntryRequest;
import com.memoria.api.service.MemoryEntryService;
import com.memoria.api.service.ResponseMapper;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/memoria/projects/{projectId}/memory")
@RequiredArgsConstructor
public class MemoryEntryController {

    private final MemoryEntryService memoryEntryService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public MemoryEntryResponse createEntry(
            @PathVariable UUID projectId,
            @Valid @RequestBody CreateMemoryEntryRequest request) {
        return ResponseMapper.toMemoryEntryResponse(memoryEntryService.createEntry(projectId, request));
    }

    @GetMapping
    public List<MemoryEntryResponse> listEntries(
            @PathVariable UUID projectId,
            @RequestParam(required = false) MemoryStatus status) {
        return memoryEntryService.listEntries(projectId, status).stream()
                .map(ResponseMapper::toMemoryEntryResponse)
                .toList();
    }

    @PutMapping("/{entryId}")
    public MemoryEntryResponse updateEntry(
            @PathVariable UUID projectId,
            @PathVariable UUID entryId,
            @RequestBody UpdateMemoryEntryRequest request) {
        return ResponseMapper.toMemoryEntryResponse(memoryEntryService.updateEntry(projectId, entryId, request));
    }

    @PostMapping("/{entryId}/supersede")
    public MemoryEntryResponse supersede(
            @PathVariable UUID projectId,
            @PathVariable UUID entryId,
            @Valid @RequestBody SupersedeMemoryEntryRequest request) {
        return ResponseMapper.toMemoryEntryResponse(
                memoryEntryService.supersede(projectId, entryId, request.newEntryId()));
    }
}
