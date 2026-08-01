package com.specweaver.api.storage;

import com.specweaver.api.exception.StorageException;
import io.minio.BucketExistsArgs;
import io.minio.GetObjectArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import io.minio.Result;
import io.minio.messages.Item;
import okhttp3.Headers;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayInputStream;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class MinioStorageServiceTest {

    @Test
    void store_uploadsContentToMinioBucket() throws Exception {
        MinioClient client = mock(MinioClient.class);
        when(client.bucketExists(any(BucketExistsArgs.class))).thenReturn(true);
        MinioStorageService service = new MinioStorageService(client, "bucket");

        String key = service.store("key", "hello".getBytes(), "text/plain");

        assertEquals("key", key);
        verify(client).putObject(any(PutObjectArgs.class));
    }

    @Test
    void store_createsBucketWhenMissing() throws Exception {
        MinioClient client = mock(MinioClient.class);
        when(client.bucketExists(any(BucketExistsArgs.class))).thenReturn(false);
        MinioStorageService service = new MinioStorageService(client, "bucket");

        service.store("key", "hello".getBytes(), "text/plain");

        verify(client).makeBucket(any(io.minio.MakeBucketArgs.class));
    }

    @Test
    void retrieve_downloadsContentFromMinio() throws Exception {
        MinioClient client = mock(MinioClient.class);
        when(client.getObject(any(GetObjectArgs.class))).thenReturn(
                new io.minio.GetObjectResponse(
                        Headers.of(), "bucket", "region", "key",
                        new ByteArrayInputStream("hello".getBytes())));
        MinioStorageService service = new MinioStorageService(client, "bucket");

        byte[] content = service.retrieve("key");

        assertArrayEquals("hello".getBytes(), content);
    }

    @Test
    void delete_removesObjectFromMinio() throws Exception {
        MinioClient client = mock(MinioClient.class);
        MinioStorageService service = new MinioStorageService(client, "bucket");

        service.delete("key");

        verify(client).removeObject(any(RemoveObjectArgs.class));
    }

    @Test
    void retrieve_throwsStorageExceptionOnMinioError() throws Exception {
        MinioClient client = mock(MinioClient.class);
        when(client.getObject(any(GetObjectArgs.class))).thenThrow(new RuntimeException("down"));
        MinioStorageService service = new MinioStorageService(client, "bucket");

        assertThrows(StorageException.class, () -> service.retrieve("key"));
    }

    @Test
    void delete_throwsStorageExceptionOnMinioError() throws Exception {
        MinioClient client = mock(MinioClient.class);
        org.mockito.Mockito.doThrow(new RuntimeException("down"))
                .when(client).removeObject(any(RemoveObjectArgs.class));
        MinioStorageService service = new MinioStorageService(client, "bucket");

        assertThrows(StorageException.class, () -> service.delete("key"));
    }

    @Test
    void generateKey_producesCorrectPathFormat() {
        MinioClient client = mock(MinioClient.class);
        MinioStorageService service = new MinioStorageService(client, "bucket");

        String key = service.generateKey("s1", "d1", "file.pdf");

        assertEquals("sessions/s1/documents/d1/file.pdf", key);
    }

    @Test
    void store_throwsStorageExceptionOnMinioError() throws Exception {
        MinioClient client = mock(MinioClient.class);
        when(client.bucketExists(any(BucketExistsArgs.class))).thenThrow(new RuntimeException("down"));
        MinioStorageService service = new MinioStorageService(client, "bucket");

        assertThrows(StorageException.class,
                () -> service.store("key", "hello".getBytes(), "text/plain"));
    }
}
