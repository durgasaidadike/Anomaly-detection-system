package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class FailoverContextTest {

    @Test
    void preservesFailureContext() {

        FailoverContext context =
                new FailoverContext(
                        "operation-501",
                        "correlation-501",
                        "flask-primary"
                );

        assertEquals(
                "operation-501",
                context.operationRequestId()
        );

        assertEquals(
                "correlation-501",
                context.correlationId()
        );

        assertEquals(
                "flask-primary",
                context.failedServiceName()
        );
    }

    @Test
    void blankOperationRequestIdIsRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverContext(
                        " ",
                        "correlation-502",
                        "flask-primary"
                )
        );
    }

    @Test
    void blankCorrelationIdIsRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverContext(
                        "operation-503",
                        " ",
                        "flask-primary"
                )
        );
    }

    @Test
    void blankFailedServiceNameIsRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverContext(
                        "operation-504",
                        "correlation-504",
                        " "
                )
        );
    }

    @Test
    void nullValuesAreRejected() {

        assertThrows(
                NullPointerException.class,
                () -> new FailoverContext(
                        null,
                        "correlation-505",
                        "flask-primary"
                )
        );
    }
}
