package com.prism.backend.security;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Modifier;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthorizationRequestTest {

    @Test
    void validRequestPreservesOperation() {

        AuthorizationRequest request =
                new AuthorizationRequest("some-operation");

        assertEquals("some-operation", request.operation());
    }

    @Test
    void requestRejectsNullOrBlankOperation() {

        assertThrows(
                NullPointerException.class,
                () -> new AuthorizationRequest(null)
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> new AuthorizationRequest(" ")
        );
    }

    @Test
    void requestIsAnImmutableRecord() {

        assertTrue(AuthorizationRequest.class.isRecord());
        assertTrue(
                Modifier.isFinal(AuthorizationRequest.class.getModifiers())
        );
    }
}
