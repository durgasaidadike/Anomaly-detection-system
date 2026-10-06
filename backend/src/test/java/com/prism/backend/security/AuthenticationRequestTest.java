package com.prism.backend.security;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Modifier;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthenticationRequestTest {

    @Test
    void validRequestPreservesOpaqueAuthenticationInput() {

        AuthenticationRequest request =
                new AuthenticationRequest("external-authentication-input");

        assertEquals(
                "external-authentication-input",
                request.authenticationInput()
        );
    }

    @Test
    void requestRejectsNullOrBlankAuthenticationInput() {

        assertThrows(
                NullPointerException.class,
                () -> new AuthenticationRequest(null)
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> new AuthenticationRequest(" ")
        );
    }

    @Test
    void requestIsAnImmutableRecord() {

        assertTrue(AuthenticationRequest.class.isRecord());
        assertTrue(
                Modifier.isFinal(AuthenticationRequest.class.getModifiers())
        );
    }
}