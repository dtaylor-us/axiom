package com.specweaver.api.storage;

import com.azure.storage.blob.BlobContainerClient;
import com.azure.storage.blob.BlobContainerClientBuilder;
import com.specweaver.api.exception.StorageException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;

/**
 * Azure Blob Storage implementation for production document blobs.
 *
 * @author OpenAI
 */
@Service
@Slf4j
@ConditionalOnProperty(
    prefix = "specweaver.storage",
    name = "type",
    havingValue = "azure-blob")
public class AzureBlobStorageService implements StorageService {

    private final BlobContainerClient containerClient;

    @Autowired
    public AzureBlobStorageService(
            @Value("${specweaver.storage.azure-blob.connection-string:}") String connectionString,
            @Value("${specweaver.storage.azure-blob.container:specweaver-documents}") String container) {
        this(new BlobContainerClientBuilder()
                .connectionString(connectionString)
                .containerName(container)
                .buildClient());
    }

    AzureBlobStorageService(BlobContainerClient containerClient) {
        this.containerClient = containerClient;
    }

    @Override
    public String store(String key, byte[] content, String contentType) {
        try {
            containerClient.createIfNotExists();
            var blobClient = containerClient.getBlobClient(key);
            blobClient.upload(new ByteArrayInputStream(content), content.length, true);
            blobClient.setHttpHeaders(new com.azure.storage.blob.models.BlobHttpHeaders()
                    .setContentType(contentType));
            return key;
        } catch (RuntimeException e) {
            log.warn("Failed to store Azure blob key={}", key, e);
            throw new StorageException("Failed to store document", e);
        }
    }

    @Override
    public byte[] retrieve(String key) {
        try {
            return containerClient.getBlobClient(key).downloadContent().toBytes();
        } catch (RuntimeException e) {
            log.warn("Failed to retrieve Azure blob key={}", key, e);
            throw new StorageException("Failed to retrieve document", e);
        }
    }

    @Override
    public void delete(String key) {
        try {
            containerClient.getBlobClient(key).deleteIfExists();
        } catch (RuntimeException e) {
            log.warn("Failed to delete Azure blob key={}", key, e);
            throw new StorageException("Failed to delete document", e);
        }
    }
}
