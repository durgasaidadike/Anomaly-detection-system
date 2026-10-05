package com.prism.backend.integration.resilience;

import java.util.Objects;

public final class DefaultFailoverPolicy
        implements FailoverPolicy {

    @Override
    public FailoverDecision evaluate(
            DownstreamFailure failure
    ) {
        Objects.requireNonNull(
                failure,
                "failure must not be null"
        );

        if (failure.failoverDisposition()
                == FailoverDisposition.NEVER) {
            return FailoverDecision.DO_NOT_FAILOVER;
        }

        return FailoverDecision.FAILOVER_ALLOWED;
    }
}
