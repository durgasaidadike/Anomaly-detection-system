package com.prism.backend.integration.resilience;

import java.util.Objects;

public class DownstreamServiceException extends RuntimeException {

    private final DownstreamFailure failure;

    public DownstreamServiceException(DownstreamFailure failure) {
        super(Objects.requireNonNull(failure, "failure must not be null").kind().name());
        this.failure = failure;
    }

    public DownstreamFailure failure() {
        return failure;
    }
}
