package com.prism.backend.dto.dashboard;

import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;

public record DashboardOverviewResponse(
        Instant asOf,
        DashboardMetrics metrics,
        List<DashboardServiceHealth> services
) {

    public DashboardOverviewResponse {
        Objects.requireNonNull(asOf, "asOf must not be null");
        Objects.requireNonNull(metrics, "metrics must not be null");
        Objects.requireNonNull(services, "services must not be null");

        List<DashboardServiceHealth> immutableServices =
                List.copyOf(services);

        if (immutableServices.stream().anyMatch(Objects::isNull)) {
            throw new NullPointerException(
                    "services must not contain null entries"
            );
        }

        if (immutableServices.size()
                != new HashSet<>(
                        immutableServices.stream()
                                .map(DashboardServiceHealth::service)
                                .toList()
                ).size()) {
            throw new IllegalArgumentException(
                    "services must not contain duplicate names"
            );
        }

        services = immutableServices;
    }
}
