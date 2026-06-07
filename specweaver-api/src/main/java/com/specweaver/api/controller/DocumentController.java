package com.specweaver.api.controller;

import com.specweaver.api.domain.model.DocumentType;
import com.specweaver.api.dto.response.DocumentResponse;
import com.specweaver.api.service.AuthenticationUserResolver;
import com.specweaver.api.service.DocumentIngestionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;

/**
 * REST endpoints for session document ingestion and deletion.
 *
 * @author OpenAI
 */
@RestController
@RequestMapping("/api/v1/sessions/{sessionId}/documents")
@RequiredArgsConstructor
public class DocumentController {

    // Limit individual file uploads to 20MB because ingestion currently reads the
    // full payload into memory before downstream processing begins.
    private static final long MAX_FILE_SIZE_BYTES = 20L * 1024L * 1024L;
    // Cap raw text submissions at roughly 500KB so request bodies stay bounded
    // even when no multipart file is attached.
    private static final int MAX_TEXT_LENGTH = 500_000;
    private static final String FILE_TOO_LARGE_MESSAGE =
            "Maximum upload size is 20MB. Split large documents before submitting.";
    private static final String TEXT_TOO_LARGE_MESSAGE =
            "Maximum text size is 500000 characters. Split large documents before submitting.";

    private final DocumentIngestionService documentIngestionService;
    private final AuthenticationUserResolver userResolver;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public DocumentResponse ingestDocument(
            @PathVariable UUID sessionId,
            @RequestParam(required = false) MultipartFile file,
            @RequestParam(required = false) String text,
            @RequestParam DocumentType documentType,
            @RequestParam(required = false) String sourceLabel,
            Authentication authentication) {
        validateUploadSize(file, text);
        return documentIngestionService.ingestDocument(
                sessionId,
                userResolver.resolveUserId(authentication),
                file,
                text,
                documentType,
                sourceLabel);
    }

    @GetMapping
    public List<DocumentResponse> listDocuments(
            @PathVariable UUID sessionId,
            Authentication authentication) {
        return documentIngestionService.listDocuments(sessionId, userResolver.resolveUserId(authentication));
    }

    @DeleteMapping("/{documentId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteDocument(
            @PathVariable UUID sessionId,
            @PathVariable UUID documentId,
            Authentication authentication) {
        documentIngestionService.deleteDocument(
                sessionId,
                documentId,
                userResolver.resolveUserId(authentication));
    }

    private void validateUploadSize(MultipartFile file, String text) {
        if (file != null && file.getSize() > MAX_FILE_SIZE_BYTES) {
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, FILE_TOO_LARGE_MESSAGE);
        }

        if (text != null && text.length() > MAX_TEXT_LENGTH) {
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, TEXT_TOO_LARGE_MESSAGE);
        }
    }
}
