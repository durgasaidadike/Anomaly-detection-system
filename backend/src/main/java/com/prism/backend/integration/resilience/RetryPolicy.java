package com.prism.backend.integration.resilience;

public interface RetryPolicy {

    RetryDecision evaluate(
            DownstreamFailure failure,
            RetryContext context
    );
}
