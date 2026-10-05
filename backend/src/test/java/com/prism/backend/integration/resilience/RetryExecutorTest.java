package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.net.ConnectException;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

class RetryExecutorTest {

    private final ScheduledExecutorService scheduler =
            Executors.newSingleThreadScheduledExecutor();

    private final RetryExecutor executor =
            new RetryExecutor(
                    new DefaultRetryPolicy(),
                    scheduler,
                    Duration.ZERO
            );

    @AfterEach
    void shutdownScheduler() {
        scheduler.shutdownNow();
    }

    @Test
    void successfulOperationRunsOnlyOnce() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {
                            attempts.incrementAndGet();

                            return CompletableFuture.completedFuture(
                                    "success"
                            );
                        },
                        context()
                );

        assertEquals(
                "success",
                result.join()
        );

        assertEquals(
                1,
                attempts.get()
        );
    }

    @Test
    void transientFailureRetriesAndThenSucceeds() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {

                            int current =
                                    attempts.incrementAndGet();

                            if (current == 1) {
                                return CompletableFuture.failedFuture(
                                        timeoutFailure()
                                );
                            }

                            return CompletableFuture.completedFuture(
                                    "recovered"
                            );
                        },
                        context()
                );

        assertEquals(
                "recovered",
                result.join()
        );

        assertEquals(
                2,
                attempts.get()
        );
    }

    @Test
    void nonIdempotentOperationMustNotRetry() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {
                            attempts.incrementAndGet();

                            return CompletableFuture.failedFuture(
                                    timeoutFailure()
                            );
                        },
                        new RetryContext(
                                0,
                                3,
                                false
                        )
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        result::join
                );

        assertInstanceOf(
                DownstreamServiceException.class,
                exception.getCause()
        );

        assertEquals(
                1,
                attempts.get()
        );
    }

    @Test
    void authenticationFailureMustNotRetry() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {
                            attempts.incrementAndGet();

                            return CompletableFuture.failedFuture(
                                    authenticationFailure()
                            );
                        },
                        context()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        result::join
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.AUTHENTICATION_FAILURE,
                downstream.failure().kind()
        );

        assertEquals(
                1,
                attempts.get()
        );
    }

    @Test
    void retryStopsAtMaximumAttemptCount() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {
                            attempts.incrementAndGet();

                            return CompletableFuture.failedFuture(
                                    timeoutFailure()
                            );
                        },
                        new RetryContext(
                                0,
                                3,
                                true
                        )
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        result::join
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.TIMEOUT,
                downstream.failure().kind()
        );

        assertEquals(
                3,
                attempts.get()
        );
    }

    @Test
    void finalRetryFailureIsPropagated() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {
                            attempts.incrementAndGet();

                            return CompletableFuture.failedFuture(
                                    connectionFailure()
                            );
                        },
                        new RetryContext(
                                0,
                                3,
                                true
                        )
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        result::join
                );

        DownstreamServiceException downstream =
                assertInstanceOf(
                        DownstreamServiceException.class,
                        exception.getCause()
                );

        assertEquals(
                DownstreamFailureKind.CONNECTION_FAILURE,
                downstream.failure().kind()
        );

        assertEquals(
                3,
                attempts.get()
        );
    }

    @Test
    void unexpectedFailureIsNotRetried() {

        AtomicInteger attempts =
                new AtomicInteger();

        CompletableFuture<String> result =
                executor.execute(
                        () -> {
                            attempts.incrementAndGet();

                            return CompletableFuture.failedFuture(
                                    new IllegalStateException(
                                            "unexpected failure"
                                    )
                            );
                        },
                        context()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        result::join
                );

        assertInstanceOf(
                IllegalStateException.class,
                exception.getCause()
        );

        assertEquals(
                1,
                attempts.get()
        );
    }

    @Test
    void negativeRetryDelayIsRejected() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new RetryExecutor(
                        new DefaultRetryPolicy(),
                        scheduler,
                        Duration.ofMillis(-1)
                )
        );
    }

    @Test
    void nullOperationResultIsHandledSafely() {

        CompletableFuture<String> result =
                executor.execute(
                        () -> null,
                        context()
                );

        CompletionException exception =
                assertThrows(
                        CompletionException.class,
                        result::join
                );

        assertInstanceOf(
                IllegalStateException.class,
                exception.getCause()
        );
    }

    private static RetryContext context() {
        return new RetryContext(
                0,
                3,
                true
        );
    }

    private static DownstreamServiceException timeoutFailure() {

        return new DownstreamServiceException(
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "retry-trace-001"
                )
        );
    }

    private static DownstreamServiceException connectionFailure() {

        return new DownstreamServiceException(
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.CONNECTION_FAILURE,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "retry-trace-002"
                )
        );
    }

    private static DownstreamServiceException authenticationFailure() {

        return new DownstreamServiceException(
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.AUTHENTICATION_FAILURE,
                        RetryDisposition.NEVER,
                        FailoverDisposition.NEVER,
                        401,
                        "retry-trace-003"
                )
        );
    }
}
