package com.prism.backend.integration.resilience;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.Objects;

public record FailoverInvocationResponse(
        int statusCode,
        JsonNode body
) {

    public FailoverInvocationResponse {
        if (statusCode < 100 || statusCode > 599) {
            throw new IllegalArgumentException(
                    "statusCode must be a valid HTTP status code"
            );
        }

        Objects.requireNonNull(
                body,
                "body must not be null"
        );
    }
}
