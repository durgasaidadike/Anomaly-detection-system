package com.prism.backend.security;

/**
 * Minimal authorization service implementation for contract testing.
 * <p>
 * This implementation serves as a placeholder to establish the authorization boundary.
 * The actual authorization policy engine will be implemented in a later chunk.
 */
public final class DefaultAuthorizationService implements AuthorizationService {

    @Override
    public void authorize(
            AuthorizationContext context,
            AuthorizationRequest request
    ) {
    }
}
