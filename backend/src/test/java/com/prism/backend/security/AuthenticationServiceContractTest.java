package com.prism.backend.security;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthenticationServiceContractTest {

    @Test
    void implementationCanAuthenticateAnIncomingRequest() {

        AuthenticationService authenticationService = request -> {
            if (!"accepted-input".equals(request.authenticationInput())) {
                throw new AuthenticationFailureException(
                        "authentication input was not accepted"
                );
            }

            return AuthenticationContext.authenticated("principal-001");
        };

        AuthenticationContext context = authenticationService.authenticate(
                new AuthenticationRequest("accepted-input")
        );

        assertEquals("principal-001", context.principalId());
        assertTrue(context.authenticated());
    }

    @Test
    void authenticationFailureIsASeparateFailureContract() {

        AuthenticationService authenticationService = request -> {
            throw new AuthenticationFailureException(
                    "authentication input was not accepted"
            );
        };

        AuthenticationFailureException exception = assertThrows(
                AuthenticationFailureException.class,
                () -> authenticationService.authenticate(
                        new AuthenticationRequest("rejected-input")
                )
        );

        assertEquals("authentication input was not accepted", exception.getMessage());
        assertTrue(exception instanceof RuntimeException);
        assertFalse(
                IllegalArgumentException.class.isAssignableFrom(
                        AuthenticationFailureException.class
                )
        );
        assertInstanceOf(
                AuthenticationFailureException.class,
                exception
        );
    }
}