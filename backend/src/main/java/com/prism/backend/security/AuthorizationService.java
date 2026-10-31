package com.prism.backend.security;

/**
 * Authorizes operations after authentication.
 */
public interface AuthorizationService {

    void authorize(
            AuthorizationContext context,
            AuthorizationRequest request
    );
}
