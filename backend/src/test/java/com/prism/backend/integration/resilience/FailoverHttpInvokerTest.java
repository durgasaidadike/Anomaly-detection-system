package com.prism.backend.integration.resilience;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.prism.backend.integration.flask.DownstreamHttpResponse;
import com.prism.backend.integration.flask.DownstreamHttpTransport;
import org.junit.jupiter.api.Test;

import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;

import static org.junit.jupiter.api.Assertions.*;

class FailoverHttpInvokerTest {

    private final ObjectMapper objectMapper =
            new ObjectMapper();

    @Test
    void successWithValidJsonObject() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                200,
                                """
                                {"result":"ok"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        Map<String, Object> payload =
                new LinkedHashMap<>();

        payload.put("key", "value");

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-701",
                        "attempt-701",
                        "correlation-701",
                        payload
                );

        FailoverInvocationResponse response =
                invoker.invoke(target, request).join();

        assertEquals(
                200,
                response.statusCode()
        );

        assertEquals(
                "ok",
                response.body().get("result").asText()
        );

        assertEquals(
                "attempt-701",
                transport.headers.get("Request-ID")
        );

        assertEquals(
                "correlation-701",
                transport.headers.get("Correlation-ID")
        );
    }

    @Test
    void successWith201Status() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                201,
                                """
                                {"created":"true"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-702",
                        "attempt-702",
                        "correlation-702",
                        Map.of("key", "value")
                );

        FailoverInvocationResponse response =
                invoker.invoke(target, request).join();

        assertEquals(
                201,
                response.statusCode()
        );
    }

    @Test
    void malformedJsonProducesInvalidResponse() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                200,
                                "{invalid json"
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-703",
                        "attempt-703",
                        "correlation-703",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.INVALID_RESPONSE,
                cause.failure().kind()
        );
    }

    @Test
    void jsonArrayProducesInvalidResponse() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                200,
                                """
                                ["array", "value"]
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-704",
                        "attempt-704",
                        "correlation-704",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.INVALID_RESPONSE,
                cause.failure().kind()
        );
    }

    @Test
    void authenticationFailureBlocksFailover() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                401,
                                """
                                {"error":"unauthorized"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-705",
                        "attempt-705",
                        "correlation-705",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.AUTHENTICATION_FAILURE,
                cause.failure().kind()
        );

        assertEquals(
                RetryDisposition.NEVER,
                cause.failure().retryDisposition()
        );

        assertEquals(
                FailoverDisposition.NEVER,
                cause.failure().failoverDisposition()
        );
    }

    @Test
    void authorizationFailureBlocksFailover() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                403,
                                """
                                {"error":"forbidden"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-706",
                        "attempt-706",
                        "correlation-706",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.AUTHORIZATION_FAILURE,
                cause.failure().kind()
        );

        assertEquals(
                FailoverDisposition.NEVER,
                cause.failure().failoverDisposition()
        );
    }

    @Test
    void validationFailureBlocksFailover() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                422,
                                """
                                {"error":"validation"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-707",
                        "attempt-707",
                        "correlation-707",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.VALIDATION_FAILURE,
                cause.failure().kind()
        );

        assertEquals(
                FailoverDisposition.NEVER,
                cause.failure().failoverDisposition()
        );
    }

    @Test
    void serviceUnavailablePermitsConditionalFailover() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                503,
                                """
                                {"error":"unavailable"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-708",
                        "attempt-708",
                        "correlation-708",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.SERVICE_UNAVAILABLE,
                cause.failure().kind()
        );

        assertEquals(
                RetryDisposition.CONDITIONAL,
                cause.failure().retryDisposition()
        );

        assertEquals(
                FailoverDisposition.CONDITIONAL,
                cause.failure().failoverDisposition()
        );
    }

    @Test
    void timeoutPermitsConditionalFailover() {

        MockTransport transport =
                new MockTransport(
                        new HttpTimeoutException("timeout")
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-709",
                        "attempt-709",
                        "correlation-709",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.TIMEOUT,
                cause.failure().kind()
        );

        assertEquals(
                RetryDisposition.CONDITIONAL,
                cause.failure().retryDisposition()
        );

        assertEquals(
                FailoverDisposition.CONDITIONAL,
                cause.failure().failoverDisposition()
        );
    }

    @Test
    void connectionFailurePermitsConditionalFailover() {

        MockTransport transport =
                new MockTransport(
                        new ConnectException("connection refused")
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-710",
                        "attempt-710",
                        "correlation-710",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.CONNECTION_FAILURE,
                cause.failure().kind()
        );

        assertEquals(
                RetryDisposition.CONDITIONAL,
                cause.failure().retryDisposition()
        );

        assertEquals(
                FailoverDisposition.CONDITIONAL,
                cause.failure().failoverDisposition()
        );
    }

    @Test
    void nullResponseProducesInvalidResponse() {

        MockTransport transport =
                new MockTransport(null);

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-711",
                        "attempt-711",
                        "correlation-711",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.INVALID_RESPONSE,
                cause.failure().kind()
        );
    }

    @Test
    void nullFutureProducesProtocolFailure() {

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        (uri, headers, body, timeout) -> null,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-712",
                        "attempt-712",
                        "correlation-712",
                        Map.of()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        () -> invoker.invoke(target, request).join()
                );

        FailoverInvocationException cause =
                assertInstanceOf(
                        FailoverInvocationException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.PROTOCOL_FAILURE,
                cause.failure().kind()
        );
    }

    @Test
    void targetEndpointPropagated() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                200,
                                """
                                {"result":"ok"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-713",
                        "attempt-713",
                        "correlation-713",
                        Map.of()
                );

        invoker.invoke(target, request).join();

        assertEquals(
                URI.create("http://127.0.0.1:5001"),
                transport.uri
        );
    }

    @Test
    void payloadSerializedCorrectly() {

        MockTransport transport =
                new MockTransport(
                        new DownstreamHttpResponse(
                                200,
                                """
                                {"result":"ok"}
                                """
                        )
                );

        FailoverHttpInvoker invoker =
                new FailoverHttpInvoker(
                        transport,
                        objectMapper,
                        Duration.ofSeconds(5)
                );

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        Map<String, Object> payload =
                new LinkedHashMap<>();

        payload.put("key", "value");

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-714",
                        "attempt-714",
                        "correlation-714",
                        payload
                );

        invoker.invoke(target, request).join();

        assertTrue(
                transport.requestBody.contains("\"key\":\"value\"")
        );
    }

    @Test
    void negativeTimeoutRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverHttpInvoker(
                        new MockTransport(
                                new DownstreamHttpResponse(
                                        200,
                                        """
                                        {"result":"ok"}
                                        """
                                )
                        ),
                        objectMapper,
                        Duration.ofSeconds(-1)
                )
        );
    }

    private static final class MockTransport
            implements DownstreamHttpTransport {

        private final Object responseOrException;
        private URI uri;
        private Map<String, String> headers;
        private String requestBody;

        private MockTransport(Object responseOrException) {
            this.responseOrException = responseOrException;
        }

        @Override
        public CompletableFuture<DownstreamHttpResponse> send(
                URI uri,
                Map<String, String> headers,
                String requestBody,
                Duration timeout
        ) {
            this.uri = uri;
            this.headers = headers;
            this.requestBody = requestBody;

            if (responseOrException instanceof DownstreamHttpResponse response) {
                return CompletableFuture.completedFuture(response);
            }

            if (responseOrException instanceof Throwable throwable) {
                return CompletableFuture.failedFuture(
                        new CompletionException(throwable)
                );
            }

            return CompletableFuture.completedFuture(null);
        }
    }
}
