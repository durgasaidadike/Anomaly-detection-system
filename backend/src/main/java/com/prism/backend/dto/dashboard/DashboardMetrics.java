package com.prism.backend.dto.dashboard;

import java.util.Objects;

public record DashboardMetrics(
        DashboardMetricSnapshot events24h,
        DashboardMetricSnapshot finalPatterns,
        DashboardMetricSnapshot anomalies,
        DashboardMetricSnapshot blockedRisks,
        DashboardMetricSnapshot completedRecoveries
) {

    public DashboardMetrics {
        Objects.requireNonNull(
                events24h,
                "events24h must not be null"
        );
        Objects.requireNonNull(
                finalPatterns,
                "finalPatterns must not be null"
        );
        Objects.requireNonNull(
                anomalies,
                "anomalies must not be null"
        );
        Objects.requireNonNull(
                blockedRisks,
                "blockedRisks must not be null"
        );
        Objects.requireNonNull(
                completedRecoveries,
                "completedRecoveries must not be null"
        );
    }
}
