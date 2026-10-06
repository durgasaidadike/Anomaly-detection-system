package com.prism.backend.security;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Modifier;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthenticationContextTest {

    @Test
    void authenticatedContextPreservesPrincipalIdentity() {

        AuthenticationContext context =
                AuthenticationContext.authenticated("principal-001");

        assertEquals("principal-001", context.principalId());
        assertTrue(context.authenticated());
    }

    @Test
    void unauthenticatedContextHasNoPrincipalIdentity() {

        AuthenticationContext context =
                AuthenticationContext.unauthenticated();

        assertNull(context.principalId());
        assertFalse(context.authenticated());
    }

    @Test
    void authenticatedContextRejectsNullOrBlankPrincipalIdentity() {

        assertThrows(
                NullPointerException.class,
                () -> AuthenticationContext.authenticated(null)
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> AuthenticationContext.authenticated(" ")
        );
    }

    @Test
    void unauthenticatedContextRejectsAnIdentity() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new AuthenticationContext("principal-002", false)
        );
    }

    @Test
    void contextIsAnImmutableRecord() {

        assertTrue(AuthenticationContext.class.isRecord());
        assertTrue(
                Modifier.isFinal(AuthenticationContext.class.getModifiers())
        );
    }
}