package com.specweaver.api.storage;

/**
 * Storage abstraction for SpecWeaver document blobs.
 */
public interface StorageService {

    /**
     * Stores document content and returns its storage key.
     *
     * @param key storage object key
     * @param content binary content
     * @param contentType content type
     * @return storage key
     */
    String store(String key, byte[] content, String contentType);

    /**
     * Retrieves stored content.
     *
     * @param key storage object key
     * @return binary content
     */
    byte[] retrieve(String key);

    /**
     * Deletes stored content.
     *
     * @param key storage object key
     */
    void delete(String key);

    /**
     * Generates the canonical document storage key.
     *
     * @param sessionId session identifier
     * @param documentId document identifier
     * @param filename original file name
     * @return deterministic storage key
     */
    default String generateKey(String sessionId, String documentId, String filename) {
        return String.format(
                "sessions/%s/documents/%s/%s",
                sessionId,
                documentId,
                filename != null ? filename : "document.txt");
    }
}
