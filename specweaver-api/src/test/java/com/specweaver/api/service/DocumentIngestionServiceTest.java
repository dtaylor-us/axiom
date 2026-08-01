package com.specweaver.api.service;

import com.specweaver.api.domain.model.DocumentStatus;
import com.specweaver.api.domain.model.DocumentType;
import com.specweaver.api.domain.model.Session;
import com.specweaver.api.domain.model.SessionDocument;
import com.specweaver.api.exception.DocumentProcessingException;
import com.specweaver.api.repository.SessionDocumentRepository;
import com.specweaver.api.storage.StorageService;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class DocumentIngestionServiceTest {

    @Mock private SessionDocumentRepository documentRepository;
    @Mock private StorageService storageService;
    @Mock private SessionService sessionService;
    private DocumentIngestionService documentIngestionService;

    @BeforeEach
    void setUp() {
        documentIngestionService = new DocumentIngestionService(
            documentRepository, storageService, sessionService);
    }

    @Test
    void extractTextFromPdf_returnsTextContent() throws Exception {
        String result = documentIngestionService.extractText(DocumentType.PDF, pdfBytes("hello pdf"), null);

        assertEquals(true, result.contains("hello pdf"));
    }

    @Test
    void extractTextFromDocx_returnsTextContent() throws Exception {
        String result = documentIngestionService.extractText(DocumentType.DOCX, docxBytes("hello docx"), null);

        assertEquals(true, result.contains("hello docx"));
    }

    @Test
    void extractTextFromPlainText_returnsTextUnchanged() {
        String result = documentIngestionService.extractText(DocumentType.PLAIN_TEXT, new byte[0], "plain");

        assertEquals("plain", result);
    }

    @Test
    void extractTextFromMarkdown_returnsTextUnchanged() {
        String result = documentIngestionService.extractText(DocumentType.MARKDOWN, new byte[0], "# heading");

        assertEquals("# heading", result);
    }

    @Test
    void extractTextFromEmail_returnsTextUnchanged() {
        String result = documentIngestionService.extractText(DocumentType.EMAIL, new byte[0], "Subject: Hi");

        assertEquals("Subject: Hi", result);
    }

    @Test
    void ingestDocument_storesDocumentAndReturnsExtractedResponse() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.save(any())).thenAnswer(invocation -> {
            SessionDocument document = invocation.getArgument(0);
            if (document.getId() == null) {
                document.setId(UUID.randomUUID());
            }
            return document;
        });
        when(storageService.generateKey(any(), any(), any())).thenReturn("key");
        when(storageService.store(eq("key"), any(), eq("text/plain"))).thenReturn("key");

        var response = documentIngestionService.ingestDocument(
                session.getId(), session.getUserId(), null, "hello",
                DocumentType.PLAIN_TEXT, "source");

        assertEquals(DocumentStatus.EXTRACTED, response.status());
        assertEquals("hello", response.extractedText());
    }

    @Test
    void ingestDocument_rejectsBinaryTypeWithoutFile() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);

        assertThrows(IllegalArgumentException.class,
                () -> documentIngestionService.ingestDocument(
                        session.getId(), session.getUserId(), null, "hello", DocumentType.PDF, "source"));
    }

    @Test
    void ingestDocument_rejectsFileForTextType() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        MockMultipartFile file = new MockMultipartFile("file", "doc.txt", "text/plain", "hello".getBytes());
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);

        assertThrows(IllegalArgumentException.class,
                () -> documentIngestionService.ingestDocument(
                        session.getId(), session.getUserId(), file, null, DocumentType.PLAIN_TEXT, "source"));
    }

    @Test
    void ingestDocument_usesSourceLabelAsMarkdownFilename() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.save(any())).thenAnswer(invocation -> {
            SessionDocument document = invocation.getArgument(0);
            if (document.getId() == null) {
                document.setId(UUID.randomUUID());
            }
            return document;
        });
        when(storageService.generateKey(any(), any(), any())).thenReturn("key");
        when(storageService.store(eq("key"), any(), eq("text/plain"))).thenReturn("key");

        var response = documentIngestionService.ingestDocument(
                session.getId(), session.getUserId(), null, "# notes", DocumentType.MARKDOWN, "Q3 Notes");

        assertEquals("q3-notes.md", response.filename());
    }

    @Test
    void ingestDocument_generatesUniqueDefaultFilenameForMarkdownWithoutSourceLabel() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.save(any())).thenAnswer(invocation -> {
            SessionDocument document = invocation.getArgument(0);
            if (document.getId() == null) {
                document.setId(UUID.randomUUID());
            }
            return document;
        });
        when(storageService.generateKey(any(), any(), any())).thenReturn("key");
        when(storageService.store(eq("key"), any(), eq("text/plain"))).thenReturn("key");

        var firstResponse = documentIngestionService.ingestDocument(
                session.getId(), session.getUserId(), null, "# one", DocumentType.MARKDOWN, null);
        var secondResponse = documentIngestionService.ingestDocument(
                session.getId(), session.getUserId(), null, "# two", DocumentType.MARKDOWN, null);

        assertNotEquals(firstResponse.filename(), secondResponse.filename());
    }

    @Test
    void listDocuments_returnsMappedResponses() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        SessionDocument document = textDocument();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findBySessionIdOrderByCreatedAtAsc(session.getId())).thenReturn(List.of(document));

        var responses = documentIngestionService.listDocuments(session.getId(), session.getUserId());

        assertEquals(1, responses.size());
        assertEquals(document.getId(), responses.getFirst().id());
    }

    @Test
    void deleteDocument_deletesStorageAndDatabase() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        SessionDocument document = textDocument();
        document.setStorageKey("key");
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findByIdAndSessionId(document.getId(), session.getId()))
                .thenReturn(Optional.of(document));

        documentIngestionService.deleteDocument(session.getId(), document.getId(), session.getUserId());

        verify(storageService).delete("key");
        verify(documentRepository).delete(document);
    }

    @Test
    void deleteDocument_deletesDatabaseWhenStorageKeyIsMissing() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        SessionDocument document = textDocument();
        when(sessionService.requireOwnedSession(session.getId(), session.getUserId())).thenReturn(session);
        when(documentRepository.findByIdAndSessionId(document.getId(), session.getId()))
                .thenReturn(Optional.of(document));

        documentIngestionService.deleteDocument(session.getId(), document.getId(), session.getUserId());

        verify(documentRepository).delete(document);
    }

    @Test
    void processDocument_callsStorageServiceStore() {
        SessionDocument document = textDocument();
        when(storageService.generateKey(any(), any(), any())).thenReturn("key");
        when(storageService.store(eq("key"), any(), eq("text/plain"))).thenReturn("key");
        when(documentRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        documentIngestionService.processDocument(document, null, "hello");

        verify(storageService).store(eq("key"), any(), eq("text/plain"));
    }

    @Test
    void processDocument_setsStatusExtractedOnSuccess() {
        SessionDocument document = textDocument();
        when(storageService.generateKey(any(), any(), any())).thenReturn("key");
        when(storageService.store(eq("key"), any(), eq("text/plain"))).thenReturn("key");
        when(documentRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        SessionDocument result = documentIngestionService.processDocument(document, null, "hello");

        assertEquals(DocumentStatus.EXTRACTED, result.getStatus());
        assertNotNull(result.getProcessedAt());
    }

    @Test
    void processDocument_setsStatusFailedOnExtractionError() {
        SessionDocument document = textDocument();
        document.setDocumentType(DocumentType.PDF);
        when(documentRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        assertThrows(DocumentProcessingException.class,
                () -> documentIngestionService.processDocument(document, null, "not pdf"));

        assertEquals(DocumentStatus.FAILED, document.getStatus());
    }

    @Test
    void processDocument_storesErrorMessageOnFailure() {
        SessionDocument document = textDocument();
        document.setDocumentType(DocumentType.PDF);
        when(documentRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        assertThrows(DocumentProcessingException.class,
                () -> documentIngestionService.processDocument(document, null, "not pdf"));

        assertNotNull(document.getErrorMessage());
    }

    private SessionDocument textDocument() {
        Session session = Session.builder().id(UUID.randomUUID()).userId(UUID.randomUUID()).build();
        return SessionDocument.builder()
                .id(UUID.randomUUID())
                .session(session)
                .documentType(DocumentType.PLAIN_TEXT)
                .filename("document.txt")
                .build();
    }

    private byte[] pdfBytes(String text) throws Exception {
        try (PDDocument document = new PDDocument();
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            PDPage page = new PDPage();
            document.addPage(page);
            try (PDPageContentStream stream = new PDPageContentStream(document, page)) {
                stream.beginText();
                stream.setFont(new PDType1Font(org.apache.pdfbox.pdmodel.font.Standard14Fonts.FontName.HELVETICA), 12);
                stream.newLineAtOffset(100, 700);
                stream.showText(text);
                stream.endText();
            }
            document.save(out);
            return out.toByteArray();
        }
    }

    private byte[] docxBytes(String text) throws Exception {
        try (XWPFDocument document = new XWPFDocument();
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            document.createParagraph().createRun().setText(text);
            document.write(out);
            return out.toByteArray();
        }
    }
}
