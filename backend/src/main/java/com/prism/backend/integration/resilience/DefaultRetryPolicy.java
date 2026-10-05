package com.prism.backend.integration.resilience;

import java.util.Objects;

public final class DefaultRetryPolicy
        implements RetryPolicy {

    @Override
    public RetryDecision evaluate(
            DownstreamFailure failure,
            RetryContext context
    ) {
        Objects.requireNonNull(
                failure,
                "failure must not be null"
        );

        Objects.requireNonNull(
                context,
                "context must not be null"
        );

        if (failure.retryDisposition()
                == RetryDisposition.NEVER) {
            return RetryDecision.DO_NOT_RETRY;
        }

        if (!context.operationIdempotent()) {
            return RetryDecision.DO_NOT_RETRY;
        }

        if (context.attemptsAlreadyMade()
                >= context.maxAttempts()) {
            return RetryDecision.DO_NOT_RETRY;
        }

        return RetryDecision.RETRY;
    }
}
