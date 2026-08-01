package com.specweaver.api.service;

import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.DocumentType;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionDocument;
import com.specweaver.api.dto.response.DocumentResponse;
import com.specweaver.api.exception.DocumentProcessingException;
import com.specweaver.api.exception.SessionNotFoundException;
import com.specweaver.api.repository.SessionDocumentRepository;
import com.specweaver.api.storage.StorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Handles document upload, blob storage, and server-side text extraction.
 *
 * @author OpenAI
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentIngestionService {

    private static final String DEFAULT_TEXT_CONTENT_TYPE = "text/plain";

    private final SessionDocumentRepository documentRepository;
    private final StorageService storageService;
    private final SessionService sessionService;

    @Transactional
    public DocumentResponse ingestDocument(
            UUID sessionId,
            UUID userId,
            MultipartFile file,
            String text,
            DocumentType documentType,
            String sourceLabel) {
        Session session = sessionService.requireOwnedSession(sessionId, userId);
        validateIngestionInput(file, text, documentType);

        SessionDocument document = documentRepository.save(SessionDocument.builder()
                .session(session)
                .documentType(documentType)
            .filename(resolveFilename(file, documentType, sourceLabel))
                .sourceLabel(sourceLabel)
                .status(DocumentStatus.PROCESSING)
                .build());

        return ResponseMapper.toDocumentResponse(processDocument(document, file, text));
    }

    @Transactional(readOnly = true)
    public List<DocumentResponse> listDocuments(UUID sessionId, UUID userId) {
        sessionService.requireOwnedSession(sessionId, userId);
        return documentRepository.findBySessionIdOrderByCreatedAtAsc(sessionId)
                .stream()
                .map(ResponseMapper::toDocumentResponse)
                .toList();
    }

    @Transactional
    public void deleteDocument(UUID sessionId, UUID documentId, UUID userId) {
        sessionService.requireOwnedSession(sessionId, userId);
        SessionDocument document = documentRepository.findByIdAndSessionId(documentId, sessionId)
                .orElseThrow(() -> new SessionNotFoundException("Document not found"));
        if (document.getStorageKey() != null) {
            storageService.delete(document.getStorageKey());
        }
        documentRepository.delete(document);
    }

    SessionDocument processDocument(SessionDocument document, MultipartFile file, String text) {
        try {
            byte[] content = resolveContent(file, text);
            String extractedText = extractText(document.getDocumentType(), content, text);
            String key = storageService.generateKey(
                    document.getSession().getId().toString(),
                    document.getId().toString(),
                    document.getFilename());
            String storedKey = storageService.store(key, content, resolveContentType(file));

            document.setStorageKey(storedKey);
            document.setExtractedText(extractedText);
            document.setStatus(DocumentStatus.EXTRACTED);
            document.setErrorMessage(null);
            document.setProcessedAt(Instant.now());
            return documentRepository.save(document);
        } catch (DocumentProcessingException e) {
            markFailed(document, e);
            throw e;
        } catch (RuntimeException e) {
            DocumentProcessingException wrapped =
                    new DocumentProcessingException("Document processing failed", e);
            markFailed(document, wrapped);
            throw wrapped;
        }
    }

    public String extractText(DocumentType documentType, byte[] content, String text) {
        return switch (documentType) {
            case PDF -> extractPdfText(content);
            case DOCX -> extractDocxText(content);
            case PLAIN_TEXT, MARKDOWN, EMAIL -> text;
        };
    }

    private void validateIngestionInput(MultipartFile file, String text, DocumentType documentType) {
        boolean hasFile = file != null && !file.isEmpty();
        boolean hasText = text != null && !text.isBlank();
        if (!hasFile && !hasText) {
            throw new IllegalArgumentException("One of file or text must be provided");
        }
        if ((documentType == DocumentType.PDF || documentType == DocumentType.DOCX) && !hasFile) {
            throw new IllegalArgumentException("Binary document types require a file");
        }
        if (hasFile && documentType != DocumentType.PDF && documentType != DocumentType.DOCX) {
            throw new IllegalArgumentException("Unsupported file type for documentType " + documentType);
        }
    }

    private byte[] resolveContent(MultipartFile file, String text) {
        try {
            if (file != null && !file.isEmpty()) {
                return file.getBytes();
            }
            return text.getBytes(StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new DocumentProcessingException("Unable to read uploaded document", e);
        }
    }

    private String resolveFilename(MultipartFile file, DocumentType documentType, String sourceLabel) {
        if (file != null && file.getOriginalFilename() != null) {
            return file.getOriginalFilename();
        }
        String extension = switch (documentType) {
            case MARKDOWN -> "md";
            case EMAIL -> "eml";
            default -> "txt";
        };
        String normalizedSourceLabel = normalizeSourceLabel(sourceLabel);
        if (normalizedSourceLabel != null) {
            return normalizedSourceLabel + "." + extension;
        }

        String uniqueSuffix = UUID.randomUUID().toString().substring(0, 8);
        return "document-" + uniqueSuffix + "." + extension;
    }

    private String normalizeSourceLabel(String sourceLabel) {
        if (sourceLabel == null) {
            return null;
        }
        String trimmedLabel = sourceLabel.trim().toLowerCase();
        if (trimmedLabel.isEmpty()) {
            return null;
        }

        String normalized = trimmedLabel
                .replaceAll("[^a-z0-9\\s-]", "")
                .replaceAll("\\s+", "-")
                .replaceAll("-+", "-")
                .replaceAll("^-|-$", "");
        if (normalized.isEmpty()) {
            return null;
        }
        return normalized;
    }

    private String resolveContentType(MultipartFile file) {
        if (file != null && file.getContentType() != null) {
            return file.getContentType();
        }
        return DEFAULT_TEXT_CONTENT_TYPE;
    }

    private String extractPdfText(byte[] content) {
        try (var document = Loader.loadPDF(content)) {
            return new PDFTextStripper().getText(document);
        } catch (IOException e) {
            throw new DocumentProcessingException("Unable to extract text from PDF", e);
        }
    }

    private String extractDocxText(byte[] content) {
        try (var document = new XWPFDocument(new ByteArrayInputStream(content));
             var extractor = new XWPFWordExtractor(document)) {
            return extractor.getText();
        } catch (IOException e) {
            throw new DocumentProcessingException("Unable to extract text from DOCX", e);
        }
    }

    private void markFailed(SessionDocument document, RuntimeException error) {
        log.warn("Document processing failed documentId={}", document.getId(), error);
        document.setStatus(DocumentStatus.FAILED);
        document.setErrorMessage(error.getMessage());
        document.setProcessedAt(Instant.now());
        documentRepository.save(document);
    }
}
