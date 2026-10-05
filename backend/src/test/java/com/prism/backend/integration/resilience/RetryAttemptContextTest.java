package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class RetryAttemptContextTest {

    @Test
    void preservesOperationAndAttemptIdentity() {

        RetryAttemptContext context =
                new RetryAttemptContext(
                        "operation-001",
                        "attempt-001",
                        "correlation-001",
                        1
                );

        assertEquals(
                "operation-001",
                context.operationRequestId()
        );

        assertEquals(
                "attempt-001",
                context.attemptRequestId()
        );

        assertEquals(
                "correlation-001",
                context.correlationId()
        );

        assertEquals(
                1,
                context.attemptNumber()
        );
    }

    @Test
    void rejectsBlankOperationRequestId() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryAttemptContext(
                        " ",
                        "attempt-001",
                        "correlation-001",
                        1
                )
        );
    }

    @Test
    void rejectsBlankAttemptRequestId() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryAttemptContext(
                        "operation-001",
                        " ",
                        "correlation-001",
                        1
                )
        );
    }

    @Test
    void rejectsBlankCorrelationId() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryAttemptContext(
                        "operation-001",
                        "attempt-001",
                        " ",
                        1
                )
        );
    }

    @Test
    void rejectsInvalidAttemptNumber() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryAttemptContext(
                        "operation-001",
                        "attempt-001",
                        "correlation-001",
                        0
                )
        );
    }

    @Test
    void retryAttemptsUseUniqueAttemptRequestIds() {

        java.util.concurrent.ScheduledExecutorService scheduler =
                java.util.concurrent.Executors
                        .newSingleThreadScheduledExecutor();

        RetryExecutor executor =
                new RetryExecutor(
                        new DefaultRetryPolicy(),
                        scheduler,
                        java.time.Duration.ZERO
                );

        List<RetryAttemptContext> attempts =
                new java.util.concurrent.CopyOnWriteArrayList<>();

        try {

            java.util.concurrent.CompletableFuture<String> result =
                    executor.execute(
                            attempt -> {

                                attempts.add(attempt);

                                if (attempt.attemptNumber() == 1) {
                                    return java.util.concurrent.CompletableFuture
                                            .failedFuture(
                                                    new DownstreamServiceException(
                                                            new DownstreamFailure(
                                                                    "flask-primary",
                                                                    DownstreamFailureKind.TIMEOUT,
                                                                    RetryDisposition.CONDITIONAL,
                                                                    FailoverDisposition.CONDITIONAL,
                                                                    null,
                                                                    "trace-201"
                                                            )
                                                    )
                                            );
                                }

                                return java.util.concurrent.CompletableFuture
                                        .completedFuture(
                                                "success"
                                        );
                            },
                            "operation-201",
                            "correlation-201",
                            new RetryContext(
                                    0,
                                    3,
                                    true
                            )
                    );

            assertEquals(
                    "success",
                    result.join()
            );

            assertEquals(
                    2,
                    attempts.size()
            );

            assertEquals(
                    "operation-201",
                    attempts.get(0).operationRequestId()
            );

            assertEquals(
                    "operation-201",
                    attempts.get(1).operationRequestId()
            );

            assertEquals(
                    "correlation-201",
                    attempts.get(0).correlationId()
            );

            assertEquals(
                    "correlation-201",
                    attempts.get(1).correlationId()
            );

            assertEquals(
                    1,
                    attempts.get(0).attemptNumber()
            );

            assertEquals(
                    2,
                    attempts.get(1).attemptNumber()
            );

            assertNotEquals(
                    attempts.get(0).attemptRequestId(),
                    attempts.get(1).attemptRequestId()
            );

        } finally {
            scheduler.shutdownNow();
        }
    }

    @Test
    void nonRetryingOperationProducesSingleAttemptIdentity() {

        java.util.concurrent.ScheduledExecutorService scheduler =
                java.util.concurrent.Executors
                        .newSingleThreadScheduledExecutor();

        RetryExecutor executor =
                new RetryExecutor(
                        new DefaultRetryPolicy(),
                        scheduler,
                        java.time.Duration.ZERO
                );

        List<RetryAttemptContext> attempts =
                new java.util.concurrent.CopyOnWriteArrayList<>();

        try {

            String result =
                    executor.execute(
                            attempt -> {

                                attempts.add(attempt);

                                return java.util.concurrent.CompletableFuture
                                        .completedFuture(
                                                "ok"
                                        );
                            },
                            "operation-202",
                            "correlation-202",
                            new RetryContext(
                                    0,
                                    3,
                                    true
                            )
                    ).join();

            assertEquals(
                    "ok",
                    result
            );

            assertEquals(
                    1,
                    attempts.size()
            );

            assertEquals(
                    1,
                    attempts.get(0).attemptNumber()
            );

        } finally {
            scheduler.shutdownNow();
        }
    }
}
