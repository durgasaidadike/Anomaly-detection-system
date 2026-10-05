package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class DownstreamFailureTest {

    @Test
    void failureModelPreservesFields() {

        DownstreamFailure failure = new DownstreamFailure(
                "flask-primary",
                DownstreamFailureKind.TIMEOUT,
                RetryDisposition.CONDITIONAL,
                FailoverDisposition.CONDITIONAL,
                null,
                "trace-001"
        );

        assertEquals("flask-primary", failure.serviceName());
        assertEquals(DownstreamFailureKind.TIMEOUT, failure.kind());
        assertEquals(RetryDisposition.CONDITIONAL, failure.retryDisposition());
        assertEquals(FailoverDisposition.CONDITIONAL, failure.failoverDisposition());
        assertEquals("trace-001", failure.traceIdentifier());
    }

    @Test
    void coreIdentityFieldsMustBePresent() {

        assertThrows(
                NullPointerException.class,
                () -> new DownstreamFailure(
                        null,
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-002"
                )
        );
    }

    @Test
    void timeoutCanPermitConditionalRetryAndFailover() {

        DownstreamFailure failure = new DownstreamFailure(
                "flask-primary",
                DownstreamFailureKind.TIMEOUT,
                RetryDisposition.CONDITIONAL,
                FailoverDisposition.CONDITIONAL,
                null,
                "trace-003"
        );

        assertEquals(RetryDisposition.CONDITIONAL, failure.retryDisposition());
        assertEquals(FailoverDisposition.CONDITIONAL, failure.failoverDisposition());
    }

    @Test
    void authorizationFailureMustNeverRetryOrFailover() {

        DownstreamFailure failure = new DownstreamFailure(
                "flask-primary",
                DownstreamFailureKind.AUTHORIZATION_FAILURE,
                RetryDisposition.NEVER,
                FailoverDisposition.NEVER,
                403,
                "trace-004"
        );

        assertEquals(RetryDisposition.NEVER, failure.retryDisposition());
        assertEquals(FailoverDisposition.NEVER, failure.failoverDisposition());
        assertEquals(403, failure.statusCode());
    }

    @Test
    void exceptionPreservesFailureModel() {

        DownstreamFailure failure = new DownstreamFailure(
                "flask-primary",
                DownstreamFailureKind.CONNECTION_FAILURE,
                RetryDisposition.CONDITIONAL,
                FailoverDisposition.CONDITIONAL,
                null,
                "trace-005"
        );

        DownstreamServiceException exception =
                new DownstreamServiceException(failure);

        assertNotNull(exception.failure());
        assertEquals(failure, exception.failure());
        assertEquals(
                DownstreamFailureKind.CONNECTION_FAILURE.name(),
                exception.getMessage()
        );
    }
}
