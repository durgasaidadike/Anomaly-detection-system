package com.prism.backend.integration.resilience;

import java.util.Map;
import java.util.Objects;

public record FailoverInvocationRequest(
        String operationRequestId,
        String attemptRequestId,
        String correlationId,
        Map<String, Object> payload
) {

    public FailoverInvocationRequest {
        requireNonBlank(
                operationRequestId,
                "operationRequestId"
        );

        requireNonBlank(
                attemptRequestId,
                "attemptRequestId"
        );

        requireNonBlank(
                correlationId,
                "correlationId"
        );

        Objects.requireNonNull(
                payload,
                "payload must not be null"
        );

        payload = Map.copyOf(payload);
    }

    private static void requireNonBlank(
            String value,
            String fieldName
    ) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                    fieldName + " must not be blank"
            );
        }
    }
}
