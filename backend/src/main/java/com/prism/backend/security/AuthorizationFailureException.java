package com.prism.backend.security;

import java.util.Objects;

/**
 * Signals that an authenticated request is not authorized to perform an operation.
 */
public final class AuthorizationFailureException extends RuntimeException {

    public AuthorizationFailureException(String message) {
        super(Objects.requireNonNull(message, "message must not be null"));
    }

    public AuthorizationFailureException(
            String message,
            Throwable cause
    ) {
        super(
                Objects.requireNonNull(message, "message must not be null"),
                cause
        );
    }
}
