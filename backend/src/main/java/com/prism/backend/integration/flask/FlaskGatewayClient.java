package com.prism.backend.integration.flask;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.prism.backend.dto.api.ApiRequestEnvelope;
import com.prism.backend.integration.resilience.DownstreamFailure;
import com.prism.backend.integration.resilience.DownstreamFailureKind;
import com.prism.backend.integration.resilience.DownstreamServiceException;
import com.prism.backend.integration.resilience.FailoverDisposition;
import com.prism.backend.integration.resilience.RetryDisposition;
import com.prism.backend.security.ServiceCredentialProvider;

import java.net.ConnectException;
import java.net.URI;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutionException;

public final class FlaskGatewayClient implements FlaskGatewayPort {

    private static final String ENDPOINT = "/analyze-event";

    private final String serviceName;
    private final URI baseUri;
    private final Duration timeout;
    private final DownstreamHttpTransport transport;
    private final ObjectMapper objectMapper;
    private final ServiceCredentialProvider credentialProvider;

    public FlaskGatewayClient(
            String serviceName,
            URI baseUri,
            Duration timeout,
            DownstreamHttpTransport transport,
            ObjectMapper objectMapper,
            ServiceCredentialProvider credentialProvider
    ) {
        this.serviceName = requireText(serviceName, "serviceName");
        this.baseUri = validateBaseUri(baseUri);
        this.timeout = validateTimeout(timeout);
        this.transport = Objects.requireNonNull(
                transport,
                "transport must not be null"
        );
        this.objectMapper = Objects.requireNonNull(
                objectMapper,
                "objectMapper must not be null"
        );
        this.credentialProvider = Objects.requireNonNull(
                credentialProvider,
                "credentialProvider must not be null"
        );
    }

    @Override
    public CompletableFuture<JsonNode> analyzeEvent(
            ApiRequestEnvelope<Map<String, Object>> request,
            String correlationId
    ) {
        return analyzeEvent(
                request,
                correlationId,
                request.requestId()
        );
    }

    public CompletableFuture<JsonNode> analyzeEvent(
            ApiRequestEnvelope<Map<String, Object>> request,
            String correlationId,
            String attemptRequestId
    ) {
        Objects.requireNonNull(request, "request must not be null");

        String traceId = requireText(
                correlationId,
                "correlationId"
        );

        if (attemptRequestId == null
                || attemptRequestId.isBlank()) {
            return CompletableFuture.failedFuture(
                    failureException(
                            DownstreamFailureKind.PROTOCOL_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            null,
                            traceId
                    )
            );
        }

        String requestBody;

        try {
            requestBody = objectMapper.writeValueAsString(
                    Objects.requireNonNull(
                            request.payload(),
                            "request payload must not be null"
                    )
            );
        } catch (JsonProcessingException exception) {
            return CompletableFuture.failedFuture(
                    failureException(
                            DownstreamFailureKind.PROTOCOL_FAILURE,
                            RetryDisposition.NEVER,
                            FailoverDisposition.NEVER,
                            null,
                            traceId
                    )
            );
        }

        Map<String, String> headers = new LinkedHashMap<>();

        String authorizationHeader =
                credentialProvider.authorizationHeader();

        if (authorizationHeader == null
                || authorizationHeader.isBlank()) {
            throw failureException(
                    DownstreamFailureKind.AUTHENTICATION_FAILURE,
                    RetryDisposition.NEVER,
                    FailoverDisposition.NEVER,
                    null,
                    traceId
            );
        }

        headers.put(
                "Authorization",
                authorizationHeader
        );

        headers.put("Content-Type", "application/json");
        headers.put("Accept", "application/json");
        headers.put("Request-ID", attemptRequestId);
        headers.put("Correlation-ID", traceId);
        headers.put("Timestamp", request.timestamp().toString());

        return transport
                .send(
                        buildEndpointUri(),
                        headers,
                        requestBody,
                        timeout
                )
                .handle((response, throwable) -> {

                    if (throwable != null) {
                        throw transportFailure(
                                unwrap(throwable),
                                traceId
                        );
                    }

                    if (response == null) {
                        throw failureException(
                                DownstreamFailureKind.INVALID_RESPONSE,
                                RetryDisposition.NEVER,
                                FailoverDisposition.NEVER,
                                null,
                                traceId
                        );
                    }

                    if (response.statusCode() < 200
                            || response.statusCode() >= 300) {
                        throw httpFailure(
                                response.statusCode(),
                                traceId
                        );
                    }

                    try {
                        JsonNode json = objectMapper.readTree(
                                response.body()
                        );

                        if (json == null || !json.isObject()) {
                            throw failureException(
                                    DownstreamFailureKind.INVALID_RESPONSE,
                                    RetryDisposition.NEVER,
                                    FailoverDisposition.NEVER,
                                    response.statusCode(),
                                    traceId
                            );
                        }

                        return json;

                    } catch (JsonProcessingException exception) {
                        throw failureException(
                                DownstreamFailureKind.INVALID_RESPONSE,
                                RetryDisposition.NEVER,
                                FailoverDisposition.NEVER,
                                response.statusCode(),
                                traceId
                        );
                    }
                });
    }

    private URI buildEndpointUri() {
        String base = baseUri.toString();

        if (base.endsWith("/")) {
            return URI.create(base.substring(0, base.length() - 1)
                    + ENDPOINT);
        }

        return URI.create(base + ENDPOINT);
    }

    private DownstreamServiceException transportFailure(
            Throwable throwable,
            String traceId
    ) {
        if (throwable instanceof HttpTimeoutException) {
            return failureException(
                    DownstreamFailureKind.TIMEOUT,
                    RetryDisposition.CONDITIONAL,
                    FailoverDisposition.CONDITIONAL,
                    null,
                    traceId
            );
        }

        if (throwable instanceof ConnectException) {
            return failureException(
                    DownstreamFailureKind.CONNECTION_FAILURE,
                    RetryDisposition.CONDITIONAL,
                    FailoverDisposition.CONDITIONAL,
                    null,
                    traceId
            );
        }

        return failureException(
                DownstreamFailureKind.CONNECTION_FAILURE,
                RetryDisposition.CONDITIONAL,
                FailoverDisposition.CONDITIONAL,
                null,
                traceId
        );
    }

    private DownstreamServiceException httpFailure(
            int statusCode,
            String traceId
    ) {
        if (statusCode == 401) {
            return failureException(
                    DownstreamFailureKind.AUTHENTICATION_FAILURE,
                    RetryDisposition.NEVER,
                    FailoverDisposition.NEVER,
                    statusCode,
                    traceId
            );
        }

        if (statusCode == 403) {
            return failureException(
                    DownstreamFailureKind.AUTHORIZATION_FAILURE,
                    RetryDisposition.NEVER,
                    FailoverDisposition.NEVER,
                    statusCode,
                    traceId
            );
        }

        if (statusCode == 400 || statusCode == 422) {
            return failureException(
                    DownstreamFailureKind.VALIDATION_FAILURE,
                    RetryDisposition.NEVER,
                    FailoverDisposition.NEVER,
                    statusCode,
                    traceId
            );
        }

        if (statusCode >= 500) {
            return failureException(
                    DownstreamFailureKind.SERVICE_UNAVAILABLE,
                    RetryDisposition.CONDITIONAL,
                    FailoverDisposition.CONDITIONAL,
                    statusCode,
                    traceId
            );
        }

        return failureException(
                DownstreamFailureKind.PROTOCOL_FAILURE,
                RetryDisposition.NEVER,
                FailoverDisposition.NEVER,
                statusCode,
                traceId
        );
    }

    private DownstreamServiceException failureException(
            DownstreamFailureKind kind,
            RetryDisposition retryDisposition,
            FailoverDisposition failoverDisposition,
            Integer statusCode,
            String traceId
    ) {
        return new DownstreamServiceException(
                new DownstreamFailure(
                        serviceName,
                        kind,
                        retryDisposition,
                        failoverDisposition,
                        statusCode,
                        traceId
                )
        );
    }

    private static Throwable unwrap(Throwable throwable) {
        Throwable current = throwable;

        while ((current instanceof CompletionException
                || current instanceof ExecutionException)
                && current.getCause() != null) {
            current = current.getCause();
        }

        return current;
    }

    private static URI validateBaseUri(URI uri) {
        Objects.requireNonNull(uri, "baseUri must not be null");

        String scheme = uri.getScheme();

        if (!"http".equalsIgnoreCase(scheme)
                && !"https".equalsIgnoreCase(scheme)) {
            throw new IllegalArgumentException(
                    "baseUri must use HTTP or HTTPS"
            );
        }

        return uri;
    }

    private static Duration validateTimeout(Duration timeout) {
        Objects.requireNonNull(
                timeout,
                "timeout must not be null"
        );

        if (timeout.isZero() || timeout.isNegative()) {
            throw new IllegalArgumentException(
                    "timeout must be positive"
            );
        }

        return timeout;
    }

    private static String requireText(
            String value,
            String fieldName
    ) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                    fieldName + " must not be blank"
            );
        }

        return value;
    }
}
