package com.prism.backend.integration.flask;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.prism.backend.dto.api.ApiRequestEnvelope;
import com.prism.backend.integration.resilience.DownstreamFailureKind;
import com.prism.backend.integration.resilience.DownstreamServiceException;
import org.junit.jupiter.api.Test;

import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;

import static org.junit.jupiter.api.Assertions.*;

class FlaskGatewayClientTest {

    private static final ObjectMapper OBJECT_MAPPER =
            new ObjectMapper();

    @Test
    void successfulRequestReturnsJsonObject() {

        FakeTransport transport = new FakeTransport(
                new DownstreamHttpResponse(
                        200,
                        """
                        {
                          "riskScore": 0.92,
                          "decision": "HIGH_RISK"
                        }
                        """
                )
        );

        FlaskGatewayClient client = client(transport);

        JsonNode result = client
                .analyzeEvent(request(), "corr-001")
                .join();

        assertTrue(result.isObject());
        assertEquals(0.92, result.get("riskScore").asDouble());
        assertEquals("HIGH_RISK", result.get("decision").asText());
    }

    @Test
    void requestPropagatesRequiredTracingHeaders() {

        FakeTransport transport = new FakeTransport(
                new DownstreamHttpResponse(
                        200,
                        """
                        {"result":"ok"}
                        """
                )
        );

        FlaskGatewayClient client = client(transport);

        client.analyzeEvent(request(), "corr-002").join();

        assertEquals(
                "req-001",
                transport.headers.get("Request-ID")
        );

        assertEquals(
                "corr-002",
                transport.headers.get("Correlation-ID")
        );

        assertEquals(
                "2026-10-05T07:30:00Z",
                transport.headers.get("Timestamp")
        );

        assertEquals(
                "application/json",
                transport.headers.get("Content-Type")
        );

        assertEquals(
                "application/json",
                transport.headers.get("Accept")
        );

        assertEquals(
                URI.create(
                        "http://127.0.0.1:5000/analyze-event"
                ),
                transport.uri
        );
    }

    @Test
    void timeoutBecomesDownstreamTimeoutFailure() {

        FakeTransport transport = new FakeTransport(
                new HttpTimeoutException("timed out")
        );

        FlaskGatewayClient client = client(transport);

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> client
                                .analyzeEvent(
                                        request(),
                                        "corr-003"
                                )
                                .join()
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.TIMEOUT,
                downstream.failure().kind()
        );
    }

    @Test
    void connectionFailureBecomesDownstreamConnectionFailure() {

        FakeTransport transport = new FakeTransport(
                new ConnectException("connection refused")
        );

        FlaskGatewayClient client = client(transport);

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> client
                                .analyzeEvent(
                                        request(),
                                        "corr-004"
                                )
                                .join()
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.CONNECTION_FAILURE,
                downstream.failure().kind()
        );
    }

    @Test
    void serverFailureBecomesServiceUnavailable() {

        FakeTransport transport = new FakeTransport(
                new DownstreamHttpResponse(
                        503,
                        """
                        {"error":"unavailable"}
                        """
                )
        );

        FlaskGatewayClient client = client(transport);

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> client
                                .analyzeEvent(
                                        request(),
                                        "corr-005"
                                )
                                .join()
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.SERVICE_UNAVAILABLE,
                downstream.failure().kind()
        );

        assertEquals(
                503,
                downstream.failure().statusCode()
        );
    }

    @Test
    void authenticationFailureMustNeverRetryOrFailover() {

        FakeTransport transport = new FakeTransport(
                new DownstreamHttpResponse(
                        401,
                        """
                        {"error":"unauthorized"}
                        """
                )
        );

        FlaskGatewayClient client = client(transport);

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> client
                                .analyzeEvent(
                                        request(),
                                        "corr-006"
                                )
                                .join()
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.AUTHENTICATION_FAILURE,
                downstream.failure().kind()
        );

        assertEquals(
                "NEVER",
                downstream.failure()
                        .retryDisposition()
                        .name()
        );

        assertEquals(
                "NEVER",
                downstream.failure()
                        .failoverDisposition()
                        .name()
        );
    }

    @Test
    void malformedJsonBecomesInvalidResponse() {

        FakeTransport transport = new FakeTransport(
                new DownstreamHttpResponse(
                        200,
                        "this-is-not-json"
                )
        );

        FlaskGatewayClient client = client(transport);

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> client
                                .analyzeEvent(
                                        request(),
                                        "corr-007"
                                )
                                .join()
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.INVALID_RESPONSE,
                downstream.failure().kind()
        );

        assertEquals(
                200,
                downstream.failure().statusCode()
        );
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
                OBJECT_MAPPER
        );
    }

    private static ApiRequestEnvelope<Map<String, Object>> request() {

        Map<String, Object> payload =
                new LinkedHashMap<>();

        payload.put("event_type", "FILE_MODIFICATION");
        payload.put("file_path", "C:\\data\\example.txt");
        payload.put("file_count", 5);
        payload.put("operation_frequency", 2);
        payload.put("unusual_time_access", 0);
        payload.put("change_size", 100);

        return new ApiRequestEnvelope<>(
                "req-001",
                Instant.parse(
                        "2026-10-05T07:30:00Z"
                ),
                "session-001",
                "user-001",
                "project-001",
                payload
        );
    }

    private static final class FakeTransport
            implements DownstreamHttpTransport {

        private final DownstreamHttpResponse response;
        private final Throwable failure;

        private URI uri;
        private Map<String, String> headers;
        private String body;

        private FakeTransport(
                DownstreamHttpResponse response
        ) {
            this.response = response;
            this.failure = null;
        }

        private FakeTransport(Throwable failure) {
            this.response = null;
            this.failure = failure;
        }

        @Override
        public CompletableFuture<DownstreamHttpResponse> send(
                URI uri,
                Map<String, String> headers,
                String requestBody,
                Duration timeout
        ) {
            this.uri = uri;
            this.headers = new LinkedHashMap<>(headers);
            this.body = requestBody;

            if (failure != null) {
                return CompletableFuture.failedFuture(
                        failure
                );
            }

            return CompletableFuture.completedFuture(
                    response
            );
        }
    }
}
