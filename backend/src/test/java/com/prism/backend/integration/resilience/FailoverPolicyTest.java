package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class FailoverPolicyTest {

    private final FailoverPolicy policy =
            new DefaultFailoverPolicy();

    @Test
    void conditionalFailurePermitsFailover() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-501"
                );

        assertEquals(
                FailoverDecision.FAILOVER_ALLOWED,
                policy.evaluate(failure)
        );
    }

    @Test
    void neverFailoverFailureBlocksFailover() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.AUTHENTICATION_FAILURE,
                        RetryDisposition.NEVER,
                        FailoverDisposition.NEVER,
                        401,
                        "trace-502"
                );

        assertEquals(
                FailoverDecision.DO_NOT_FAILOVER,
                policy.evaluate(failure)
        );
    }

    @Test
    void authorizationFailureBlocksFailover() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.AUTHORIZATION_FAILURE,
                        RetryDisposition.NEVER,
                        FailoverDisposition.NEVER,
                        403,
                        "trace-503"
                );

        assertEquals(
                FailoverDecision.DO_NOT_FAILOVER,
                policy.evaluate(failure)
        );
    }

    @Test
    void validationFailureBlocksFailover() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.VALIDATION_FAILURE,
                        RetryDisposition.NEVER,
                        FailoverDisposition.NEVER,
                        422,
                        "trace-504"
                );

        assertEquals(
                FailoverDecision.DO_NOT_FAILOVER,
                policy.evaluate(failure)
        );
    }

    @Test
    void serviceUnavailableMayPermitFailover() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.SERVICE_UNAVAILABLE,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        503,
                        "trace-505"
                );

        assertEquals(
                FailoverDecision.FAILOVER_ALLOWED,
                policy.evaluate(failure)
        );
    }

    @Test
    void nullFailureIsRejected() {

        assertThrows(
                NullPointerException.class,
                () -> policy.evaluate(null)
        );
    }
}
