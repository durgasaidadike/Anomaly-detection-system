package com.prism.backend.security;

import java.util.Objects;

/**
 * Opaque authentication input supplied at the application boundary.
 *
 * <p>The value intentionally has no token-format semantics. A later
 * authentication mechanism may interpret it without changing this contract.</p>
 */
public record AuthenticationRequest(
        String authenticationInput
) {

    public AuthenticationRequest {
        Objects.requireNonNull(
                authenticationInput,
                "authenticationInput must not be null"
        );

        if (authenticationInput.isBlank()) {
            throw new IllegalArgumentException(
                    "authenticationInput must not be blank"
            );
        }
    }
}