package com.prism.backend.security;

/**
 * Authenticates opaque request input before authorization and business processing.
 */
public interface AuthenticationService {

    AuthenticationContext authenticate(
            AuthenticationRequest request
    );
}