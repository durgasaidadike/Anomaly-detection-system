package com.prism.backend.dto.dashboard;

import java.time.Instant;
import java.util.Objects;

public record DashboardMetricSnapshot(
        DashboardMetricAvailability availability,
        Long count,
        Instant observedAt,
        DashboardMetricWindow window
) {

    public DashboardMetricSnapshot(
            DashboardMetricAvailability availability,
            Long count,
            Instant observedAt
    ) {
        this(availability, count, observedAt, null);
    }

    public DashboardMetricSnapshot {
        Objects.requireNonNull(
                availability,
                "availability must not be null"
        );

        if (count != null && count < 0) {
            throw new IllegalArgumentException(
                    "count must not be negative"
            );
        }

        if (availability == DashboardMetricAvailability.AVAILABLE
                || availability == DashboardMetricAvailability.STALE) {
            if (count == null) {
                throw new IllegalArgumentException(
                        "count is required when metric is available"
                );
            }

            if (observedAt == null) {
                throw new IllegalArgumentException(
                        "observedAt is required when metric is available"
                );
            }
        } else if (count != null) {
            throw new IllegalArgumentException(
                    "count must be null when metric is unavailable"
            );
        } else if (observedAt != null) {
            throw new IllegalArgumentException(
                    "observedAt must be null when metric is unavailable"
            );
        }
    }
}
