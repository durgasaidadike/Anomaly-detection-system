package com.prism.backend.integration.flask;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.prism.backend.dto.api.ApiRequestEnvelope;
import com.prism.backend.integration.resilience.DefaultIdempotencyPolicy;
import com.prism.backend.integration.resilience.DefaultRetryPolicy;
import com.prism.backend.integration.resilience.RetryExecutor;
import com.prism.backend.security.ServiceCredentialProvider;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

class ResilientFlaskGatewayTest {

    private static final ObjectMapper OBJECT_MAPPER =
            new ObjectMapper();

    private static final ServiceCredentialProvider
            CREDENTIAL_PROVIDER =
            () -> "Bearer test-token";

    @Test
    void unsupportedIdempotencyDoesNotTriggerRetry() {

        ScheduledExecutorService scheduler =
                Executors.newSingleThreadScheduledExecutor();

        try {

            AtomicInteger invocations =
                    new AtomicInteger();

            TrackingTransport transport =
                    new TrackingTransport(
                            () -> {
                                invocations.incrementAndGet();

                                return new DownstreamHttpResponse(
                                        503,
                                        """
                                        {"error":"unavailable"}
                                        """
                                );
                            }
                    );

            FlaskGatewayClient delegate =
                    client(transport);

            RetryExecutor retryExecutor =
                    new RetryExecutor(
                            new DefaultRetryPolicy(),
                            scheduler,
                            Duration.ZERO
                    );

            ResilientFlaskGateway gateway =
                    new ResilientFlaskGateway(
                            delegate,
                            retryExecutor,
                            new DefaultIdempotencyPolicy()
                    );

            CompletableFuture<JsonNode> result =
                    gateway.analyzeEvent(
                            request(),
                            "correlation-401"
                    );

            assertThrows(
                    Exception.class,
                    result::join
            );

            assertEquals(
                    1,
                    invocations.get()
            );

        } finally {
            scheduler.shutdownNow();
        }
    }

    @Test
    void unsupportedIdempotencyStillPreservesCorrelationId() {

        ScheduledExecutorService scheduler =
                Executors.newSingleThreadScheduledExecutor();

        try {

            TrackingTransport transport =
                    new TrackingTransport(
                            () -> new DownstreamHttpResponse(
                                    200,
                                    """
                                    {"result":"ok"}
                                    """
                            )
                    );

            ResilientFlaskGateway gateway =
                    new ResilientFlaskGateway(
                            client(transport),
                            new RetryExecutor(
                                    new DefaultRetryPolicy(),
                                    scheduler,
                                    Duration.ZERO
                            ),
                            new DefaultIdempotencyPolicy()
                    );

            JsonNode result =
                    gateway.analyzeEvent(
                            request(),
                            "correlation-402"
                    ).join();

            assertEquals(
                    "ok",
                    result.get("result").asText()
            );

            assertEquals(
                    "correlation-402",
                    transport.headers.get(
                            "Correlation-ID"
                    )
            );

        } finally {
            scheduler.shutdownNow();
        }
    }

    @Test
    void downstreamRequestUsesServiceCredential() {

        ScheduledExecutorService scheduler =
                Executors.newSingleThreadScheduledExecutor();

        try {

            TrackingTransport transport =
                    new TrackingTransport(
                            () -> new DownstreamHttpResponse(
                                    200,
                                    """
                                    {"result":"ok"}
                                    """
                            )
                    );

            ResilientFlaskGateway gateway =
                    new ResilientFlaskGateway(
                            client(transport),
                            new RetryExecutor(
                                    new DefaultRetryPolicy(),
                                    scheduler,
                                    Duration.ZERO
                            ),
                            new DefaultIdempotencyPolicy()
                    );

            gateway.analyzeEvent(
                    request(),
                    "correlation-403"
            ).join();

            assertEquals(
                    "Bearer test-token",
                    transport.headers.get(
                            "Authorization"
                    )
            );

        } finally {
            scheduler.shutdownNow();
        }
    }

    @Test
    void successfulUnsupportedOperationStillInvokesOnlyOnce() {

        ScheduledExecutorService scheduler =
                Executors.newSingleThreadScheduledExecutor();

        try {

            AtomicInteger invocations =
                    new AtomicInteger();

            TrackingTransport transport =
                    new TrackingTransport(
                            () -> {
                                invocations.incrementAndGet();

                                return new DownstreamHttpResponse(
                                        200,
                                        """
                                        {"result":"success"}
                                        """
                                );
                            }
                    );

            ResilientFlaskGateway gateway =
                    new ResilientFlaskGateway(
                            client(transport),
                            new RetryExecutor(
                                    new DefaultRetryPolicy(),
                                    scheduler,
                                    Duration.ZERO
                            ),
                            new DefaultIdempotencyPolicy()
                    );

            gateway.analyzeEvent(
                    request(),
                    "correlation-404"
            ).join();

            assertEquals(
                    1,
                    invocations.get()
            );

        } finally {
            scheduler.shutdownNow();
        }
    }

    private static FlaskGatewayClient client(
            DownstreamHttpTransport transport
    ) {
        return new FlaskGatewayClient(
                "flask-primary",
                URI.create(
                        "http://127.0.0.1:5000"
                ),
                Duration.ofSeconds(5),
                transport,
                OBJECT_MAPPER,
                CREDENTIAL_PROVIDER
        );
    }

    private static ApiRequestEnvelope<Map<String, Object>>
    request() {

        Map<String, Object> payload =
                new LinkedHashMap<>();

        payload.put(
                "event_type",
                "FILE_MODIFICATION"
        );

        payload.put(
                "file_path",
                "C:\\data\\example.txt"
        );

        payload.put(
                "file_count",
                5
        );

        payload.put(
                "operation_frequency",
                2
        );

        payload.put(
                "unusual_time_access",
                0
        );

        payload.put(
                "change_size",
                100
        );

        return new ApiRequestEnvelope<>(
                "operation-401",
                Instant.parse(
                        "2026-10-05T07:30:00Z"
                ),
                "session-401",
                "user-401",
                "project-401",
                payload
        );
    }

    private static final class TrackingTransport
            implements DownstreamHttpTransport {

        private final java.util.function.Supplier
                <DownstreamHttpResponse> responseSupplier;

        private Map<String, String> headers =
                Map.of();

        private TrackingTransport(
                java.util.function.Supplier
                        <DownstreamHttpResponse> responseSupplier
        ) {
            this.responseSupplier =
                    responseSupplier;
        }

        @Override
        public CompletableFuture<DownstreamHttpResponse> send(
                URI uri,
                Map<String, String> headers,
                String requestBody,
                Duration timeout
        ) {
            this.headers =
                    new LinkedHashMap<>(headers);

            return CompletableFuture.completedFuture(
                    responseSupplier.get()
            );
        }
    }
}
