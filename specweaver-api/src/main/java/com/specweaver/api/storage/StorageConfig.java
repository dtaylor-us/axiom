package com.specweaver.api.storage;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Selects the StorageService implementation from STORAGE_TYPE.
 */
@Configuration
public class StorageConfig {

    @Value("${specweaver.storage.type:minio}")
    private String storageType;

    /**
     * Wires the active storage implementation.
     *
     * @param minioService local MinIO implementation
     * @param azureService production Azure Blob implementation
     * @return selected storage service
     */
    @Bean
    public StorageService storageService(
            ObjectProvider<MinioStorageService> minioService,
            ObjectProvider<AzureBlobStorageService> azureService) {
        return switch (storageType) {
            case "azure-blob" -> azureService.getIfAvailable(() -> {
                throw new IllegalStateException("Azure Blob storage is configured but no Azure storage bean is available");
            });
            default -> minioService.getIfAvailable(() -> {
                throw new IllegalStateException("MinIO storage is configured but no MinIO storage bean is available");
            });
        };
    }
}
