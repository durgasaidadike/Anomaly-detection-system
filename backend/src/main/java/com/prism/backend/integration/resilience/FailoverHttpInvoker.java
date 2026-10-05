package com.prism.backend.integration.resilience;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.prism.backend.integration.flask.DownstreamHttpResponse;
import com.prism.backend.integration.flask.DownstreamHttpTransport;

import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeoutException;

public final class FailoverHttpInvoker
        implements FailoverInvoker {

    private final DownstreamHttpTransport transport;
    private final ObjectMapper objectMapper;
    private final Duration timeout;

    public FailoverHttpInvoker(
            DownstreamHttpTransport transport,
            ObjectMapper objectMapper,
            Duration timeout
    ) {
        this.transport = Objects.requireNonNull(
                transport,
                "transport must not be null"
        );

        this.objectMapper = Objects.requireNonNull(
                objectMapper,
                "objectMapper must not be null"
        );

        this.timeout = Objects.requireNonNull(
                timeout,
                "timeout must not be null"
        );

        if (timeout.isZero() || timeout.isNegative()) {
            throw new IllegalArgumentException(
                    "timeout must be positive"
            );
        }
    }

    @Override
    public CompletableFuture<FailoverInvocationResponse> invoke(
            FailoverTarget target,
            FailoverInvocationRequest request
    ) {
        Objects.requireNonNull(
                target,
                "target must not be null"
        );

        Objects.requireNonNull(
                request,
                "request must not be null"
        );

        final String requestBody;

        try {
            requestBody = objectMapper.writeValueAsString(
                    request.payload()
            );
        } catch (Exception exception) {
            return CompletableFuture.failedFuture(
                    failure(
                            target.serviceName(),
                            DownstreamFailureKind.PROTOCOL_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            null,
                            request.correlationId()
                    )
            );
        }

        Map<String, String> headers = new HashMap<>();

        headers.put(
                "Content-Type",
                "application/json"
        );

        headers.put(
                "Accept",
                "application/json"
        );

        headers.put(
                "Request-ID",
                request.attemptRequestId()
        );

        headers.put(
                "Correlation-ID",
                request.correlationId()
        );

        final CompletableFuture<DownstreamHttpResponse>
                transportFuture;

        try {
            transportFuture = transport.send(
                    target.endpoint(),
                    Map.copyOf(headers),
                    requestBody,
                    timeout
            );
        } catch (Exception exception) {
            return CompletableFuture.failedFuture(
                    mapTransportFailure(
                            target.serviceName(),
                            exception,
                            request.correlationId()
                    )
            );
        }

        if (transportFuture == null) {
            return CompletableFuture.failedFuture(
                    failure(
                            target.serviceName(),
                            DownstreamFailureKind.PROTOCOL_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            null,
                            request.correlationId()
                    )
            );
        }

        return transportFuture
                .thenCompose(response ->
                        handleResponse(
                                target.serviceName(),
                                response,
                                request.correlationId()
                        )
                )
                .exceptionallyCompose(exception -> {

                    Throwable cause = unwrap(exception);

                    if (cause instanceof
                            FailoverInvocationException) {
                        return CompletableFuture.failedFuture(
                                cause
                        );
                    }

                    return CompletableFuture.failedFuture(
                            mapTransportFailure(
                                    target.serviceName(),
                                    cause,
                                    request.correlationId()
                            )
                    );
                });
    }

    private CompletableFuture<FailoverInvocationResponse>
    handleResponse(
            String serviceName,
            DownstreamHttpResponse response,
            String correlationId
    ) {

        if (response == null) {
            return CompletableFuture.failedFuture(
                    failure(
                            serviceName,
                            DownstreamFailureKind.INVALID_RESPONSE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            null,
                            correlationId
                    )
            );
        }

        int statusCode = response.statusCode();

        if (statusCode >= 200 && statusCode < 300) {

            try {
                JsonNode body = objectMapper.readTree(
                        response.body()
                );

                if (body == null || !body.isObject()) {
                    return CompletableFuture.failedFuture(
                            failure(
                                    serviceName,
                                    DownstreamFailureKind.INVALID_RESPONSE,
                                    RetryDisposition.NEVER,
                                    FailoverDisposition.NEVER,
                                    statusCode,
                                    correlationId
                            )
                    );
                }

                return CompletableFuture.completedFuture(
                        new FailoverInvocationResponse(
                                statusCode,
                                body
                        )
                );

            } catch (Exception exception) {
                return CompletableFuture.failedFuture(
                        failure(
                                serviceName,
                                DownstreamFailureKind.INVALID_RESPONSE,
                                RetryDisposition.NEVER,
                                FailoverDisposition.NEVER,
                                statusCode,
                                correlationId
                        )
                );
            }
        }

        if (statusCode == 401) {
            return CompletableFuture.failedFuture(
                    failure(
                            serviceName,
                            DownstreamFailureKind.AUTHENTICATION_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            statusCode,
                            correlationId
                    )
            );
        }

        if (statusCode == 403) {
            return CompletableFuture.failedFuture(
                    failure(
                            serviceName,
                            DownstreamFailureKind.AUTHORIZATION_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            statusCode,
                            correlationId
                    )
            );
        }

        if (statusCode == 400 || statusCode == 422) {
            return CompletableFuture.failedFuture(
                    failure(
                            serviceName,
                            DownstreamFailureKind.VALIDATION_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            statusCode,
                            correlationId
                    )
            );
        }

        if (statusCode >= 500) {
            return CompletableFuture.failedFuture(
                    failure(
                            serviceName,
                            DownstreamFailureKind.SERVICE_UNAVAILABLE,
                            RetryDisposition.CONDITIONAL,
                            FailoverDisposition.CONDITIONAL,
                            statusCode,
                            correlationId
                    )
            );
        }

        return CompletableFuture.failedFuture(
                failure(
                        serviceName,
                        DownstreamFailureKind.PROTOCOL_FAILURE,
                        RetryDisposition.NEVER,
                        FailoverDisposition.NEVER,
                        statusCode,
                        correlationId
                )
        );
    }

    private FailoverInvocationException
    mapTransportFailure(
            String serviceName,
            Throwable exception,
            String correlationId
    ) {

        Throwable cause = unwrap(exception);

        if (cause instanceof HttpTimeoutException
                || cause instanceof TimeoutException) {

            return failure(
                    serviceName,
                    DownstreamFailureKind.TIMEOUT,
                    RetryDisposition.CONDITIONAL,
                    FailoverDisposition.CONDITIONAL,
                    null,
                    correlationId
            );
        }

        if (cause instanceof ConnectException) {

            return failure(
                    serviceName,
                    DownstreamFailureKind.CONNECTION_FAILURE,
                    RetryDisposition.CONDITIONAL,
                    FailoverDisposition.CONDITIONAL,
                    null,
                    correlationId
            );
        }

        return failure(
                serviceName,
                DownstreamFailureKind.UNKNOWN,
                RetryDisposition.NEVER,
                FailoverDisposition.NEVER,
                null,
                correlationId
        );
    }

    private FailoverInvocationException failure(
            String serviceName,
            DownstreamFailureKind kind,
            RetryDisposition retryDisposition,
            FailoverDisposition failoverDisposition,
            Integer statusCode,
            String correlationId
    ) {

        return new FailoverInvocationException(
                new DownstreamFailure(
                        serviceName,
                        kind,
                        retryDisposition,
                        failoverDisposition,
                        statusCode,
                        correlationId
                )
        );
    }

    private static Throwable unwrap(
            Throwable throwable
    ) {

        Throwable current = throwable;

        while ((current instanceof CompletionException
                || current instanceof ExecutionException)
                && current.getCause() != null) {

            current = current.getCause();
        }

        return current;
    }
}
