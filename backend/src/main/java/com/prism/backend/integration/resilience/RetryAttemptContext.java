package com.prism.backend.integration.resilience;

import java.util.Objects;

public record RetryAttemptContext(
        String operationRequestId,
        String attemptRequestId,
        String correlationId,
        int attemptNumber
) {

    public RetryAttemptContext {
        requireText(
                operationRequestId,
                "operationRequestId"
        );

        requireText(
                attemptRequestId,
                "attemptRequestId"
        );

        requireText(
                correlationId,
                "correlationId"
        );

        if (attemptNumber <= 0) {
            throw new IllegalArgumentException(
                    "attemptNumber must be greater than zero"
            );
        }
    }

    private static void requireText(
            String value,
            String fieldName
    ) {
        Objects.requireNonNull(
                value,
                fieldName + " must not be null"
        );

        if (value.isBlank()) {
            throw new IllegalArgumentException(
                    fieldName + " must not be blank"
            );
        }
    }
}
