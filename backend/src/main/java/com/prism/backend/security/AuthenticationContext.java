package com.prism.backend.security;

import java.util.Objects;

/**
 * Immutable security context established for an incoming request.
 */
public record AuthenticationContext(
        String principalId,
        boolean authenticated
) {

    public AuthenticationContext {
        if (authenticated) {
            Objects.requireNonNull(
                    principalId,
                    "principalId must not be null for an authenticated context"
            );

            if (principalId.isBlank()) {
                throw new IllegalArgumentException(
                        "principalId must not be blank for an authenticated context"
                );
            }
        } else if (principalId != null) {
            throw new IllegalArgumentException(
                    "principalId must be null for an unauthenticated context"
            );
        }
    }

    public static AuthenticationContext authenticated(
            String principalId
    ) {
        return new AuthenticationContext(principalId, true);
    }

    public static AuthenticationContext unauthenticated() {
        return new AuthenticationContext(null, false);
    }
}