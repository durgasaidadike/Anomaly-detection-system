package com.prism.backend.integration.resilience;

import java.util.Objects;

public record DownstreamFailure(
        String serviceName,
        DownstreamFailureKind kind,
        RetryDisposition retryDisposition,
        FailoverDisposition failoverDisposition,
        Integer statusCode,
        String traceIdentifier
) {

    public DownstreamFailure {
        Objects.requireNonNull(serviceName, "serviceName must not be null");
        Objects.requireNonNull(kind, "kind must not be null");
        Objects.requireNonNull(retryDisposition, "retryDisposition must not be null");
        Objects.requireNonNull(failoverDisposition, "failoverDisposition must not be null");
        Objects.requireNonNull(traceIdentifier, "traceIdentifier must not be null");
    }
}
