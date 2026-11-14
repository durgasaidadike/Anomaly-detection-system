package com.prism.backend.service.dashboard;

import com.prism.backend.dto.dashboard.DashboardMetricAvailability;
import com.prism.backend.dto.dashboard.DashboardMetricSnapshot;
import com.prism.backend.dto.dashboard.DashboardOverviewResponse;
import com.prism.backend.dto.dashboard.DashboardServiceName;
import com.prism.backend.dto.dashboard.DashboardServiceStatus;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;

class DashboardOverviewServiceTest {

    private final DashboardOverviewService service =
            new DashboardOverviewService();

    @Test
    void overviewContainsFiveMetricSnapshots() {
        DashboardOverviewResponse response = service.getOverview();

        List<DashboardMetricSnapshot> snapshots = List.of(
                response.metrics().events24h(),
                response.metrics().finalPatterns(),
                response.metrics().anomalies(),
                response.metrics().blockedRisks(),
                response.metrics().completedRecoveries()
        );

        assertEquals(5, snapshots.size());
    }

    @Test
    void unconfiguredMetricsNeverContainFabricatedCounts() {
        DashboardOverviewResponse response = service.getOverview();

        List<DashboardMetricSnapshot> snapshots = List.of(
                response.metrics().events24h(),
                response.metrics().finalPatterns(),
                response.metrics().anomalies(),
                response.metrics().blockedRisks(),
                response.metrics().completedRecoveries()
        );

        for (DashboardMetricSnapshot snapshot : snapshots) {
            assertEquals(
                    DashboardMetricAvailability.NOT_CONFIGURED,
                    snapshot.availability()
            );
            assertNull(snapshot.count());
            assertNull(snapshot.observedAt());
        }
    }

    @Test
    void overviewContainsAllSixServiceHealthEntries() {
        DashboardOverviewResponse response = service.getOverview();

        assertEquals(6, response.services().size());
        assertEquals(
                6,
                response.services().stream()
                        .map(service -> service.service())
                        .distinct()
                        .count()
        );
    }

    @Test
    void springBootIsReportedAsUp() {
        DashboardOverviewResponse response = service.getOverview();

        var springBoot = response.services().stream()
                .filter(service ->
                        service.service() == DashboardServiceName.SPRING_BOOT
                )
                .findFirst()
                .orElseThrow();

        assertEquals(DashboardServiceStatus.UP, springBoot.status());
        assertNotNull(springBoot.observedAt());
    }

    @Test
    void unprobedServicesRemainUnknown() {
        DashboardOverviewResponse response = service.getOverview();

        for (var serviceHealth : response.services()) {
            if (serviceHealth.service() != DashboardServiceName.SPRING_BOOT) {
                assertEquals(
                        DashboardServiceStatus.UNKNOWN,
                        serviceHealth.status()
                );
                assertNull(serviceHealth.observedAt());
            }
        }
    }

    @Test
    void overviewHasAnAsOfTimestamp() {
        assertNotNull(service.getOverview().asOf());
    }
}
