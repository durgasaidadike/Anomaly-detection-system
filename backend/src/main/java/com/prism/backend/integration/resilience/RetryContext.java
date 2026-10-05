package com.prism.backend.integration.resilience;

public record RetryContext(
        int attemptsAlreadyMade,
        int maxAttempts,
        boolean operationIdempotent
) {

    public RetryContext {
        if (attemptsAlreadyMade < 0) {
            throw new IllegalArgumentException(
                    "attemptsAlreadyMade must not be negative"
            );
        }

        if (maxAttempts <= 0) {
            throw new IllegalArgumentException(
                    "maxAttempts must be greater than zero"
            );
        }

        if (attemptsAlreadyMade > maxAttempts) {
            throw new IllegalArgumentException(
                    "attemptsAlreadyMade must not exceed maxAttempts"
            );
        }
    }
}
