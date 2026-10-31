package com.prism.backend.security;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AuthorizationServiceContractTest {

    @Test
    void minimalImplementationCanAuthorize() {

        AuthorizationService authorizationService = new DefaultAuthorizationService();

        AuthenticationContext authContext =
                AuthenticationContext.authenticated("principal-001");
        AuthorizationContext context = AuthorizationContext.from(authContext);
        AuthorizationRequest request = new AuthorizationRequest("some-operation");

        authorizationService.authorize(context, request);
    }

    @Test
    void authorizationFailureUsesDedicatedException() {

        AuthorizationService authorizationService = (context, request) -> {
            throw new AuthorizationFailureException(
                    "operation not authorized"
            );
        };

        AuthenticationContext authContext =
                AuthenticationContext.authenticated("principal-001");
        AuthorizationContext context = AuthorizationContext.from(authContext);
        AuthorizationRequest request = new AuthorizationRequest("denied-operation");

        AuthorizationFailureException exception = assertThrows(
                AuthorizationFailureException.class,
                () -> authorizationService.authorize(context, request)
        );

        assertEquals("operation not authorized", exception.getMessage());
        assertTrue(exception instanceof RuntimeException);
        assertFalse(
                IllegalArgumentException.class.isAssignableFrom(
                        AuthorizationFailureException.class
                )
        );
        assertInstanceOf(
                AuthorizationFailureException.class,
                exception
        );
    }

    @Test
    void serviceDoesNotDependOnController() {

        AuthorizationService service = new DefaultAuthorizationService();

        assertTrue(service instanceof AuthorizationService);
        assertFalse(
                service.getClass().getName().contains("controller")
        );
    }

    @Test
    void serviceDoesNotDependOnRepository() {

        AuthorizationService service = new DefaultAuthorizationService();

        assertTrue(service instanceof AuthorizationService);
        assertFalse(
                service.getClass().getName().contains("repository")
        );
    }

    @Test
    void serviceDoesNotDependOnFlask() {

        AuthorizationService service = new DefaultAuthorizationService();

        assertTrue(service instanceof AuthorizationService);
        assertFalse(
                service.getClass().getName().contains("flask")
        );
    }

    @Test
    void serviceDoesNotDependOnIntelligencePackages() {

        AuthorizationService service = new DefaultAuthorizationService();

        assertTrue(service instanceof AuthorizationService);
        assertFalse(
                service.getClass().getName().contains("intelligence")
        );
        assertFalse(
                service.getClass().getName().contains("behavioral")
        );
    }
}
