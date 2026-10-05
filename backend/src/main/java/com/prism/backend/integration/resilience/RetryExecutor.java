package com.prism.backend.integration.resilience;

import java.time.Duration;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;
import java.util.function.Supplier;

public final class RetryExecutor {

    private final RetryPolicy retryPolicy;
    private final ScheduledExecutorService scheduler;
    private final Duration retryDelay;

    public RetryExecutor(
            RetryPolicy retryPolicy,
            ScheduledExecutorService scheduler,
            Duration retryDelay
    ) {
        this.retryPolicy = Objects.requireNonNull(
                retryPolicy,
                "retryPolicy must not be null"
        );

        this.scheduler = Objects.requireNonNull(
                scheduler,
                "scheduler must not be null"
        );

        this.retryDelay = Objects.requireNonNull(
                retryDelay,
                "retryDelay must not be null"
        );

        if (retryDelay.isNegative()) {
            throw new IllegalArgumentException(
                    "retryDelay must not be negative"
            );
        }
    }

    public <T> CompletableFuture<T> execute(
            Supplier<CompletableFuture<T>> operation,
            RetryContext initialContext
    ) {
        Objects.requireNonNull(
                operation,
                "operation must not be null"
        );

        return execute(
                ignored -> operation.get(),
                UUID.randomUUID().toString(),
                UUID.randomUUID().toString(),
                initialContext
        );
    }

    public <T> CompletableFuture<T> execute(
            Function<RetryAttemptContext, CompletableFuture<T>> operation,
            String operationRequestId,
            String correlationId,
            RetryContext initialContext
    ) {
        Objects.requireNonNull(
                operation,
                "operation must not be null"
        );

        requireText(
                operationRequestId,
                "operationRequestId"
        );

        requireText(
                correlationId,
                "correlationId"
        );

        Objects.requireNonNull(
                initialContext,
                "initialContext must not be null"
        );

        if (initialContext.attemptsAlreadyMade()
                >= initialContext.maxAttempts()) {
            throw new IllegalArgumentException(
                    "initial retry context has no remaining attempts"
            );
        }

        return executeAttempt(
                operation,
                operationRequestId,
                correlationId,
                initialContext
        );
    }

    private <T> CompletableFuture<T> executeAttempt(
            Function<RetryAttemptContext,
                    CompletableFuture<T>> operation,
            String operationRequestId,
            String correlationId,
            RetryContext context
    ) {

        RetryAttemptContext attemptContext =
                new RetryAttemptContext(
                        operationRequestId,
                        UUID.randomUUID().toString(),
                        correlationId,
                        context.attemptsAlreadyMade() + 1
                );

        CompletableFuture<T> operationFuture;

        try {
            operationFuture = operation.apply(
                    attemptContext
            );

            if (operationFuture == null) {
                return CompletableFuture.failedFuture(
                        new IllegalStateException(
                                "retry operation returned null future"
                        )
                );
            }

        } catch (Throwable throwable) {
            operationFuture =
                    CompletableFuture.failedFuture(throwable);
        }

        return operationFuture.handle(
                (result, throwable) -> {

                    if (throwable == null) {
                        return CompletableFuture.completedFuture(
                                result
                        );
                    }

                    Throwable cause =
                            unwrap(throwable);

                    if (!(cause
                            instanceof DownstreamServiceException downstreamException)) {

                        return CompletableFuture.failedFuture(
                                cause
                        );
                    }

                    RetryContext afterFailure =
                            new RetryContext(
                                    context.attemptsAlreadyMade() + 1,
                                    context.maxAttempts(),
                                    context.operationIdempotent()
                            );

                    RetryDecision decision =
                            retryPolicy.evaluate(
                                    downstreamException.failure(),
                                    afterFailure
                            );

                    if (decision
                            == RetryDecision.DO_NOT_RETRY) {

                        return CompletableFuture.failedFuture(
                                downstreamException
                        );
                    }

                    return scheduleRetry(
                            operation,
                            operationRequestId,
                            correlationId,
                            afterFailure
                    );
                }
        ).thenCompose(future -> (CompletableFuture<T>) future);
    }

    private <T> CompletableFuture<T> scheduleRetry(
            Function<RetryAttemptContext,
                    CompletableFuture<T>> operation,
            String operationRequestId,
            String correlationId,
            RetryContext context
    ) {

        CompletableFuture<T> scheduledResult =
                new CompletableFuture<>();

        try {

            scheduler.schedule(
                    () -> executeAttempt(
                            operation,
                            operationRequestId,
                            correlationId,
                            context
                    ).whenComplete(
                            (result, throwable) -> {

                                if (throwable == null) {
                                    scheduledResult.complete(
                                            result
                                    );
                                } else {
                                    scheduledResult.completeExceptionally(
                                            unwrap(throwable)
                                    );
                                }
                            }
                    ),
                    retryDelay.toNanos(),
                    TimeUnit.NANOSECONDS
            );

        } catch (RejectedExecutionException exception) {

            scheduledResult.completeExceptionally(
                    exception
            );
        }

        return scheduledResult;
    }

    private static Throwable unwrap(Throwable throwable) {

        Throwable current = throwable;

        while (current instanceof CompletionException
                && current.getCause() != null) {

            current = current.getCause();
        }

        return current;
    }

    private static void requireText(
            String value,
            String fieldName
    ) {

        Objects.requireNonNull(
                value,
                fieldName + " must not be null"
        );

        if (value.isBlank()) {
            throw new IllegalArgumentException(
                    fieldName + " must not be blank"
            );
        }
    }
}
