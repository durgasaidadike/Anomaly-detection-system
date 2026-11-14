package com.prism.backend.dto.dashboard;

import java.time.Instant;
import java.util.Objects;

public record DashboardServiceHealth(
        DashboardServiceName service,
        DashboardServiceStatus status,
        Instant observedAt
) {

    public DashboardServiceHealth {
        Objects.requireNonNull(service, "service must not be null");
        Objects.requireNonNull(status, "status must not be null");

        if (status == DashboardServiceStatus.UNKNOWN
                && observedAt != null) {
            throw new IllegalArgumentException(
                    "observedAt must be null for UNKNOWN status"
            );
        }

        if (status != DashboardServiceStatus.UNKNOWN
                && observedAt == null) {
            throw new IllegalArgumentException(
                    "observedAt is required for known status"
            );
        }
    }
}
