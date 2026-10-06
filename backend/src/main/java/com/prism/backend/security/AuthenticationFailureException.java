package com.prism.backend.security;

import java.util.Objects;

/**
 * Signals that an incoming request could not be authenticated.
 */
public final class AuthenticationFailureException extends RuntimeException {

    public AuthenticationFailureException(String message) {
        super(Objects.requireNonNull(message, "message must not be null"));
    }

    public AuthenticationFailureException(
            String message,
            Throwable cause
    ) {
        super(
                Objects.requireNonNull(message, "message must not be null"),
                cause
        );
    }
}