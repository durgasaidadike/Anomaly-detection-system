package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class RetryPolicyTest {

    private final RetryPolicy policy =
            new DefaultRetryPolicy();

    @Test
    void transientTimeoutCanBeRetriedWhenOperationIsIdempotent() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-101"
                );

        RetryContext context =
                new RetryContext(
                        1,
                        3,
                        true
                );

        assertEquals(
                RetryDecision.RETRY,
                policy.evaluate(failure, context)
        );
    }

    @Test
    void neverRetryFailureMustNeverBeRetried() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.AUTHENTICATION_FAILURE,
                        RetryDisposition.NEVER,
                        FailoverDisposition.NEVER,
                        401,
                        "trace-102"
                );

        RetryContext context =
                new RetryContext(
                        1,
                        3,
                        true
                );

        assertEquals(
                RetryDecision.DO_NOT_RETRY,
                policy.evaluate(failure, context)
        );
    }

    @Test
    void nonIdempotentOperationMustNotBeRetried() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-103"
                );

        RetryContext context =
                new RetryContext(
                        1,
                        3,
                        false
                );

        assertEquals(
                RetryDecision.DO_NOT_RETRY,
                policy.evaluate(failure, context)
        );
    }

    @Test
    void exhaustedRetryBudgetMustNotRetry() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.CONNECTION_FAILURE,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-104"
                );

        RetryContext context =
                new RetryContext(
                        3,
                        3,
                        true
                );

        assertEquals(
                RetryDecision.DO_NOT_RETRY,
                policy.evaluate(failure, context)
        );
    }

    @Test
    void retryIsPermittedBeforeBudgetIsExhausted() {

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.SERVICE_UNAVAILABLE,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        503,
                        "trace-105"
                );

        RetryContext context =
                new RetryContext(
                        2,
                        3,
                        true
                );

        assertEquals(
                RetryDecision.RETRY,
                policy.evaluate(failure, context)
        );
    }

    @Test
    void retryContextRejectsNegativeAttemptCount() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryContext(
                        -1,
                        3,
                        true
                )
        );
    }

    @Test
    void retryContextRejectsInvalidMaximumAttempts() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryContext(
                        0,
                        0,
                        true
                )
        );
    }

    @Test
    void retryContextRejectsAttemptsBeyondMaximum() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryContext(
                        4,
                        3,
                        true
                )
        );
    }
}
