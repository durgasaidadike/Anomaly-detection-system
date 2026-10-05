package com.prism.backend.integration.resilience;

import java.util.Objects;

public record IdempotencyContext(
        String operationRequestId,
        IdempotencySupport support,
        boolean protectionVerified
) {

    public IdempotencyContext {
        Objects.requireNonNull(
                operationRequestId,
                "operationRequestId must not be null"
        );

        if (operationRequestId.isBlank()) {
            throw new IllegalArgumentException(
                    "operationRequestId must not be blank"
            );
        }

        Objects.requireNonNull(
                support,
                "support must not be null"
        );
    }
}
