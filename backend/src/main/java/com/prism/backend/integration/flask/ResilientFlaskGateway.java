package com.prism.backend.integration.flask;

import com.fasterxml.jackson.databind.JsonNode;
import com.prism.backend.dto.api.ApiRequestEnvelope;
import com.prism.backend.integration.resilience.IdempotencyContext;
import com.prism.backend.integration.resilience.IdempotencyPolicy;
import com.prism.backend.integration.resilience.RetryContext;
import com.prism.backend.integration.resilience.RetryExecutor;

import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;

public final class ResilientFlaskGateway {

    private final FlaskGatewayClient delegate;
    private final RetryExecutor retryExecutor;
    private final IdempotencyPolicy idempotencyPolicy;

    public ResilientFlaskGateway(
            FlaskGatewayClient delegate,
            RetryExecutor retryExecutor,
            IdempotencyPolicy idempotencyPolicy
    ) {
        this.delegate = Objects.requireNonNull(
                delegate,
                "delegate must not be null"
        );

        this.retryExecutor = Objects.requireNonNull(
                retryExecutor,
                "retryExecutor must not be null"
        );

        this.idempotencyPolicy = Objects.requireNonNull(
                idempotencyPolicy,
                "idempotencyPolicy must not be null"
        );
    }

    public CompletableFuture<JsonNode> analyzeEvent(
            ApiRequestEnvelope<Map<String, Object>> request,
            String correlationId
    ) {
        Objects.requireNonNull(
                request,
                "request must not be null"
        );

        Objects.requireNonNull(
                correlationId,
                "correlationId must not be null"
        );

        IdempotencyContext idempotencyContext =
                new IdempotencyContext(
                        request.requestId(),
                        com.prism.backend.integration.resilience
                                .IdempotencySupport.UNSUPPORTED,
                        false
                );

        if (!idempotencyPolicy.permitsRetry(
                idempotencyContext
        )) {
            return delegate.analyzeEvent(
                    request,
                    correlationId
            );
        }

        return retryExecutor.execute(
                attempt -> delegate.analyzeEvent(
                        request,
                        correlationId,
                        attempt.attemptRequestId()
                ),
                request.requestId(),
                correlationId,
                new RetryContext(
                        0,
                        3,
                        true
                )
        );
    }
}
