package com.prism.backend.integration.resilience;

import java.net.URI;
import java.util.Objects;

public record FailoverTarget(
        String serviceName,
        URI endpoint
) {

    public FailoverTarget {
        requireNonBlank(serviceName, "serviceName");

        Objects.requireNonNull(
                endpoint,
                "endpoint must not be null"
        );

        String scheme = endpoint.getScheme();

        if (!"http".equalsIgnoreCase(scheme)
                && !"https".equalsIgnoreCase(scheme)) {
            throw new IllegalArgumentException(
                    "endpoint must use HTTP or HTTPS"
            );
        }
    }

    private static void requireNonBlank(
            String value,
            String fieldName
    ) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                    fieldName + " must not be blank"
            );
        }
    }
}
