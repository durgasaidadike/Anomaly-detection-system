package com.prism.backend.integration.resilience;

import java.util.Objects;
import java.util.Optional;

public record FailoverCoordinationResult(
        FailoverCoordinationStatus status,
        FailoverInvocationResponse response
) {

    public FailoverCoordinationResult {
        Objects.requireNonNull(
                status,
                "status must not be null"
        );

        if (status == FailoverCoordinationStatus.INVOKED) {
            Objects.requireNonNull(
                    response,
                    "response must not be null when status is INVOKED"
            );
        } else if (response != null) {
            throw new IllegalArgumentException(
                    "response must be null unless status is INVOKED"
            );
        }
    }

    public Optional<FailoverInvocationResponse> responseOptional() {
        return Optional.ofNullable(response);
    }
}
