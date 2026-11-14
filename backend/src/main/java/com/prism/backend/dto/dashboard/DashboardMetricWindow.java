package com.prism.backend.dto.dashboard;

import java.time.Instant;
import java.util.Objects;

public record DashboardMetricWindow(
        Instant startInclusive,
        Instant endExclusive
) {

    public DashboardMetricWindow {
        Objects.requireNonNull(
                startInclusive,
                "startInclusive must not be null"
        );
        Objects.requireNonNull(
                endExclusive,
                "endExclusive must not be null"
        );

        if (!startInclusive.isBefore(endExclusive)) {
            throw new IllegalArgumentException(
                    "startInclusive must be before endExclusive"
            );
        }
    }
}
