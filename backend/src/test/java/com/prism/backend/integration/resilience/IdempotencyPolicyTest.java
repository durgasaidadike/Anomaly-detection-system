package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class IdempotencyPolicyTest {

    private final IdempotencyPolicy policy =
            new DefaultIdempotencyPolicy();

    @Test
    void supportedOperationPermitsRetry() {

        IdempotencyContext context =
                new IdempotencyContext(
                        "operation-301",
                        IdempotencySupport.SUPPORTED,
                        false
                );

        assertTrue(
                policy.permitsRetry(context)
        );
    }

    @Test
    void requiredOperationWithoutProtectionMustNotPermitRetry() {

        IdempotencyContext context =
                new IdempotencyContext(
                        "operation-302",
                        IdempotencySupport.REQUIRED,
                        false
                );

        assertFalse(
                policy.permitsRetry(context)
        );
    }

    @Test
    void requiredOperationWithVerifiedProtectionPermitsRetry() {

        IdempotencyContext context =
                new IdempotencyContext(
                        "operation-303",
                        IdempotencySupport.REQUIRED,
                        true
                );

        assertTrue(
                policy.permitsRetry(context)
        );
    }

    @Test
    void unsupportedOperationMustNotPermitRetry() {

        IdempotencyContext context =
                new IdempotencyContext(
                        "operation-304",
                        IdempotencySupport.UNSUPPORTED,
                        true
                );

        assertFalse(
                policy.permitsRetry(context)
        );
    }

    @Test
    void blankOperationRequestIdIsRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new IdempotencyContext(
                        " ",
                        IdempotencySupport.SUPPORTED,
                        false
                )
        );
    }

    @Test
    void nullSupportIsRejected() {

        assertThrows(
                NullPointerException.class,
                () -> new IdempotencyContext(
                        "operation-305",
                        null,
                        false
                )
        );
    }

    @Test
    void nullContextIsRejected() {

        assertThrows(
                NullPointerException.class,
                () -> policy.permitsRetry(null)
        );
    }
}
