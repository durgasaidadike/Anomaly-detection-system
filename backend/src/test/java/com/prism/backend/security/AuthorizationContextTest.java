package com.prism.backend.security;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Modifier;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthorizationContextTest {

    @Test
    void authenticatedContextIsAccepted() {

        AuthenticationContext authContext =
                AuthenticationContext.authenticated("principal-001");

        AuthorizationContext context =
                AuthorizationContext.from(authContext);

        assertEquals(authContext, context.authenticationContext());
    }

    @Test
    void unauthenticatedContextIsRejected() {

        AuthenticationContext authContext =
                AuthenticationContext.unauthenticated();

        assertThrows(
                IllegalArgumentException.class,
                () -> AuthorizationContext.from(authContext)
        );
    }

    @Test
    void nullContextIsRejected() {

        assertThrows(
                NullPointerException.class,
                () -> AuthorizationContext.from(null)
        );
    }

    @Test
    void contextIsAnImmutableRecord() {

        assertTrue(AuthorizationContext.class.isRecord());
        assertTrue(
                Modifier.isFinal(AuthorizationContext.class.getModifiers())
        );
    }
}
