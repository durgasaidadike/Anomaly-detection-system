package com.prism.backend.integration.resilience;

public interface IdempotencyPolicy {

    boolean permitsRetry(IdempotencyContext context);
}
