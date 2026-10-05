package com.prism.backend.integration.resilience;

public interface FailoverPolicy {

    FailoverDecision evaluate(
            DownstreamFailure failure
    );
}
