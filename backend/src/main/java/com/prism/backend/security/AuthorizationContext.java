package com.prism.backend.security;

import java.util.Objects;

/**
 * Immutable security context for authorization decisions.
 */
public record AuthorizationContext(
        AuthenticationContext authenticationContext
) {

    public AuthorizationContext {
        Objects.requireNonNull(
                authenticationContext,
                "authenticationContext must not be null"
        );

        if (!authenticationContext.authenticated()) {
            throw new IllegalArgumentException(
                    "authenticationContext must be authenticated for authorization"
            );
        }
    }

    public static AuthorizationContext from(
            AuthenticationContext authenticationContext
    ) {
        return new AuthorizationContext(authenticationContext);
    }
}
