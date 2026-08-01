package com.specweaver.api.storage;

import com.specweaver.api.exception.StorageException;
import io.minio.BucketExistsArgs;
import io.minio.GetObjectArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.ByteArrayInputStream;

/**
 * MinIO-backed local implementation of document blob storage.
 *
 * @author OpenAI
 */
@Service
@Slf4j
@ConditionalOnProperty(
    prefix = "specweaver.storage",
    name = "type",
    havingValue = "minio",
    matchIfMissing = true)
public class MinioStorageService implements StorageService {

    private final MinioClient minioClient;
    private final String bucket;

    @Autowired
    public MinioStorageService(
            @Value("${specweaver.storage.minio.endpoint:http://minio:9000}") String endpoint,
            @Value("${specweaver.storage.minio.access-key:minioadmin}") String accessKey,
            @Value("${specweaver.storage.minio.secret-key:minioadmin}") String secretKey,
            @Value("${specweaver.storage.minio.bucket:specweaver-documents}") String bucket) {
        this(MinioClient.builder()
                .endpoint(endpoint)
                .credentials(accessKey, secretKey)
                .build(), bucket);
    }

    MinioStorageService(MinioClient minioClient, String bucket) {
        this.minioClient = minioClient;
        this.bucket = bucket;
    }

    @Override
    public String store(String key, byte[] content, String contentType) {
        try {
            ensureBucketExists();
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(bucket)
                    .object(key)
                    .contentType(contentType)
                    .stream(new ByteArrayInputStream(content), content.length, -1)
                    .build());
            return key;
        } catch (Exception e) {
            log.warn("Failed to store document key={}", key, e);
            throw new StorageException("Failed to store document", e);
        }
    }

    @Override
    public byte[] retrieve(String key) {
        try (var stream = minioClient.getObject(GetObjectArgs.builder()
                .bucket(bucket)
                .object(key)
                .build())) {
            return stream.readAllBytes();
        } catch (Exception e) {
            log.warn("Failed to retrieve document key={}", key, e);
            throw new StorageException("Failed to retrieve document", e);
        }
    }

    @Override
    public void delete(String key) {
        try {
            minioClient.removeObject(RemoveObjectArgs.builder()
                    .bucket(bucket)
                    .object(key)
                    .build());
        } catch (Exception e) {
            log.warn("Failed to delete document key={}", key, e);
            throw new StorageException("Failed to delete document", e);
        }
    }

    private void ensureBucketExists() throws Exception {
        boolean exists = minioClient.bucketExists(BucketExistsArgs.builder()
                .bucket(bucket)
                .build());
        if (!exists) {
            minioClient.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
        }
    }
}
