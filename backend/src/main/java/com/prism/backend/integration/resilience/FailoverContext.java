package com.prism.backend.integration.resilience;

import java.util.Objects;

public record FailoverContext(
        String operationRequestId,
        String correlationId,
        String failedServiceName
) {

    public FailoverContext {
        requireText(
                operationRequestId,
                "operationRequestId"
        );

        requireText(
                correlationId,
                "correlationId"
        );

        requireText(
                failedServiceName,
                "failedServiceName"
        );
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
