package com.prism.backend.integration.resilience;

import java.util.Objects;

public final class DefaultIdempotencyPolicy
        implements IdempotencyPolicy {

    @Override
    public boolean permitsRetry(
            IdempotencyContext context
    ) {
        Objects.requireNonNull(
                context,
                "context must not be null"
        );

        return switch (context.support()) {

            case SUPPORTED ->
                    true;

            case REQUIRED ->
                    context.protectionVerified();

            case UNSUPPORTED ->
                    false;
        };
    }
}
