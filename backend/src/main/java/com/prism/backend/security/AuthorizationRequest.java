package com.prism.backend.security;

import java.util.Objects;

/**
 * Immutable request describing the operation being authorized.
 */
public record AuthorizationRequest(
        String operation
) {

    public AuthorizationRequest {
        Objects.requireNonNull(operation, "operation must not be null");

        if (operation.isBlank()) {
            throw new IllegalArgumentException(
                    "operation must not be blank"
            );
        }
    }
}
