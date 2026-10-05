package com.prism.backend.integration.resilience;

public final class FailoverInvocationException
        extends RuntimeException {

    private final DownstreamFailure failure;

    public FailoverInvocationException(
            DownstreamFailure failure
    ) {
        super(
                "Failover invocation failed for service: "
                        + failure.serviceName()
                        + " ("
                        + failure.kind()
                        + ")"
        );

        this.failure = failure;
    }

    public DownstreamFailure failure() {
        return failure;
    }
}
