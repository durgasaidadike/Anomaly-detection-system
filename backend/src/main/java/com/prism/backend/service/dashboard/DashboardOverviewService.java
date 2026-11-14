package com.prism.backend.service.dashboard;

import com.prism.backend.dto.dashboard.DashboardMetricAvailability;
import com.prism.backend.dto.dashboard.DashboardMetricSnapshot;
import com.prism.backend.dto.dashboard.DashboardMetrics;
import com.prism.backend.dto.dashboard.DashboardOverviewResponse;
import com.prism.backend.dto.dashboard.DashboardServiceHealth;
import com.prism.backend.dto.dashboard.DashboardServiceName;
import com.prism.backend.dto.dashboard.DashboardServiceStatus;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;

@Service
public class DashboardOverviewService {

    public DashboardOverviewResponse getOverview() {
        Instant asOf = Instant.now();

        DashboardMetrics metrics = new DashboardMetrics(
                notConfiguredMetric(),
                notConfiguredMetric(),
                notConfiguredMetric(),
                notConfiguredMetric(),
                notConfiguredMetric()
        );

        List<DashboardServiceHealth> services = List.of(
                new DashboardServiceHealth(
                        DashboardServiceName.SPRING_BOOT,
                        DashboardServiceStatus.UP,
                        asOf
                ),
                unknownService(DashboardServiceName.FLASK),
                unknownService(DashboardServiceName.MONGODB),
                unknownService(DashboardServiceName.WATCHDOG),
                unknownService(DashboardServiceName.ML_ENGINE),
                unknownService(DashboardServiceName.RECOVERY_MANAGER)
        );

        return new DashboardOverviewResponse(asOf, metrics, services);
    }

    private DashboardMetricSnapshot notConfiguredMetric() {
        return new DashboardMetricSnapshot(
                DashboardMetricAvailability.NOT_CONFIGURED,
                null,
                null,
                null
        );
    }

    private DashboardServiceHealth unknownService(
            DashboardServiceName serviceName
    ) {
        return new DashboardServiceHealth(
                serviceName,
                DashboardServiceStatus.UNKNOWN,
                null
        );
    }
}
