package com.specweaver.api.controller;

import com.specweaver.api.config.GlobalExceptionHandler;
import com.specweaver.api.config.SecurityConfig;
import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.DocumentType;
import com.specweaver.api.dto.response.DocumentResponse;
import com.specweaver.api.security.GatewayHeaderAuthFilter;
import com.specweaver.api.security.JwtAuthFilter;
import com.specweaver.api.security.JwtService;
import com.specweaver.api.service.AuthenticationUserResolver;
import com.specweaver.api.service.DocumentIngestionService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DocumentController.class)
@Import({SecurityConfig.class, GatewayHeaderAuthFilter.class, JwtAuthFilter.class, JwtService.class,
        GlobalExceptionHandler.class, AuthenticationUserResolver.class})
@TestPropertySource(properties = {
        "axiom.gateway.bypass=false",
        "security.jwt.secret=super-secret-dev-key-change-in-prod-must-be-at-least-32-bytes"
})
class DocumentControllerTest {

    private static final int MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;

    @Autowired private MockMvc mockMvc;
    @MockBean private DocumentIngestionService documentIngestionService;

    @Test
    void postDocumentsWithPlainText_returnsCreated() throws Exception {
        UUID userId = UUID.randomUUID();
        when(documentIngestionService.ingestDocument(any(), any(), any(), any(), any(), any()))
                .thenReturn(document(DocumentType.PLAIN_TEXT));

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .param("text", "requirements")
                        .param("documentType", "PLAIN_TEXT")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.documentType").value("PLAIN_TEXT"));
    }

    @Test
    void postDocumentsWithPdfFile_returnsCreated() throws Exception {
        UUID userId = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile("file", "doc.pdf", "application/pdf", "pdf".getBytes());
        when(documentIngestionService.ingestDocument(any(), any(), any(), any(), any(), any()))
                .thenReturn(document(DocumentType.PDF));

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .file(file)
                        .param("documentType", "PDF")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.documentType").value("PDF"));
    }

    @Test
    void postDocumentsWithDocxFile_returnsCreated() throws Exception {
        UUID userId = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile("file", "doc.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx".getBytes());
        when(documentIngestionService.ingestDocument(any(), any(), any(), any(), any(), any()))
                .thenReturn(document(DocumentType.DOCX));

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .file(file)
                        .param("documentType", "DOCX")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.documentType").value("DOCX"));
    }

    @Test
    void uploadDocumentReturns413WhenFileTooLarge() throws Exception {
        UUID userId = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "large.pdf",
                "application/pdf",
                new byte[MAX_FILE_SIZE_BYTES + 1]);

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .file(file)
                        .param("documentType", "PDF")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isPayloadTooLarge());

        verifyNoInteractions(documentIngestionService);
    }

    @Test
    void uploadDocumentReturns413WhenTextTooLong() throws Exception {
        UUID userId = UUID.randomUUID();
        String oversizedText = "a".repeat(500_001);

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .param("text", oversizedText)
                        .param("documentType", "PLAIN_TEXT")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isPayloadTooLarge());

        verifyNoInteractions(documentIngestionService);
    }

    @Test
    void uploadDocumentAcceptsFileAtExactLimit() throws Exception {
        UUID userId = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "boundary.pdf",
                "application/pdf",
                new byte[MAX_FILE_SIZE_BYTES]);
        when(documentIngestionService.ingestDocument(any(), any(), any(), any(), any(), any()))
                .thenReturn(document(DocumentType.PDF));

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .file(file)
                        .param("documentType", "PDF")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.documentType").value("PDF"));
    }

    @Test
    void postDocumentsWithoutFileOrText_returnsBadRequest() throws Exception {
        UUID userId = UUID.randomUUID();
        when(documentIngestionService.ingestDocument(any(), any(), any(), any(), any(), any()))
                .thenThrow(new IllegalArgumentException("One of file or text must be provided"));

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .param("documentType", "PLAIN_TEXT")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isBadRequest());
    }

    @Test
    void postDocumentsWithUnsupportedType_returnsBadRequest() throws Exception {
        UUID userId = UUID.randomUUID();
        MockMultipartFile file = new MockMultipartFile("file", "doc.txt", MediaType.TEXT_PLAIN_VALUE, "x".getBytes());
        when(documentIngestionService.ingestDocument(any(), any(), any(), any(), any(), any()))
                .thenThrow(new IllegalArgumentException("Unsupported file type"));

        mockMvc.perform(multipart("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .file(file)
                        .param("documentType", "PLAIN_TEXT")
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isBadRequest());
    }

    @Test
    void getDocuments_returnsDocumentList() throws Exception {
        UUID userId = UUID.randomUUID();
        when(documentIngestionService.listDocuments(any(), any()))
                .thenReturn(List.of(document(DocumentType.PLAIN_TEXT)));

        mockMvc.perform(get("/api/v1/sessions/{sessionId}/documents", UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    void deleteDocument_returnsNoContent() throws Exception {
        UUID userId = UUID.randomUUID();
        doNothing().when(documentIngestionService).deleteDocument(any(), any(), any());

        mockMvc.perform(delete("/api/v1/sessions/{sessionId}/documents/{documentId}",
                        UUID.randomUUID(), UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isNoContent());
    }

    @Test
    void deleteDocumentFromAnotherUsersSession_returnsForbidden() throws Exception {
        UUID userId = UUID.randomUUID();
        doThrow(new AccessDeniedException("wrong user"))
                .when(documentIngestionService).deleteDocument(any(), any(), any());

        mockMvc.perform(delete("/api/v1/sessions/{sessionId}/documents/{documentId}",
                        UUID.randomUUID(), UUID.randomUUID())
                        .header("X-Axiom-User-Id", userId.toString()))
                .andExpect(status().isForbidden());
    }

    private DocumentResponse document(DocumentType documentType) {
        return new DocumentResponse(
                UUID.randomUUID(), documentType, "doc", "source", "key", "text",
                DocumentStatus.EXTRACTED, null, Instant.now(), Instant.now());
    }
}
