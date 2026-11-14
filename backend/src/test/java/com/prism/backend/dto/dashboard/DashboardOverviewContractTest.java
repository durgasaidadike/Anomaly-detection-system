package com.prism.backend.dto.dashboard;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DashboardOverviewContractTest {

    private static final Instant OBSERVED_AT =
            Instant.parse("2026-11-14T16:30:00Z");

    private final ObjectMapper objectMapper =
            new ObjectMapper()
                    .registerModule(new JavaTimeModule());

    @Test
    void available_and_stale_metrics_require_values_and_observation_time() {
        DashboardMetricSnapshot available =
                new DashboardMetricSnapshot(
                        DashboardMetricAvailability.AVAILABLE,
                        0L,
                        OBSERVED_AT
                );
        DashboardMetricSnapshot stale =
                new DashboardMetricSnapshot(
                        DashboardMetricAvailability.STALE,
                        4L,
                        OBSERVED_AT
                );

        assertEquals(0L, available.count());
        assertEquals(4L, stale.count());
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricSnapshot(
                        DashboardMetricAvailability.AVAILABLE,
                        null,
                        OBSERVED_AT
                )
        );
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricSnapshot(
                        DashboardMetricAvailability.STALE,
                        1L,
                        null
                )
        );
    }

    @Test
    void unavailable_metrics_do_not_accept_fabricated_counts() {
        DashboardMetricSnapshot unavailable =
                new DashboardMetricSnapshot(
                        DashboardMetricAvailability.UNAVAILABLE,
                        null,
                        null
                );

        assertEquals(
                DashboardMetricAvailability.UNAVAILABLE,
                unavailable.availability()
        );
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricSnapshot(
                        DashboardMetricAvailability.NOT_CONFIGURED,
                        0L,
                        null
                )
        );
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricSnapshot(
                        DashboardMetricAvailability.UNAVAILABLE,
                        null,
                        OBSERVED_AT
                )
        );
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricSnapshot(
                        DashboardMetricAvailability.NOT_CONFIGURED,
                        null,
                        OBSERVED_AT
                )
        );
    }

    @Test
    void metric_counts_and_windows_are_validated() {
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricSnapshot(
                        DashboardMetricAvailability.AVAILABLE,
                        -1L,
                        OBSERVED_AT
                )
        );

        Instant start = Instant.parse("2026-11-14T16:00:00Z");
        Instant end = Instant.parse("2026-11-14T17:00:00Z");
        DashboardMetricWindow window =
                new DashboardMetricWindow(start, end);

        DashboardMetricSnapshot snapshot =
                new DashboardMetricSnapshot(
                        DashboardMetricAvailability.AVAILABLE,
                        0L,
                        OBSERVED_AT,
                        window
                );

        assertEquals(window, snapshot.window());
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardMetricWindow(end, start)
        );
    }

    @Test
    void overview_copies_services_and_rejects_duplicate_names() {
        DashboardServiceHealth springBoot =
                new DashboardServiceHealth(
                        DashboardServiceName.SPRING_BOOT,
                        DashboardServiceStatus.UP,
                        OBSERVED_AT
                );
        DashboardServiceHealth flask =
                new DashboardServiceHealth(
                        DashboardServiceName.FLASK,
                        DashboardServiceStatus.UNKNOWN,
                        null
                );
        List<DashboardServiceHealth> services =
                new ArrayList<>(List.of(springBoot, flask));

        DashboardOverviewResponse overview =
                new DashboardOverviewResponse(
                        OBSERVED_AT,
                        availableMetrics(),
                        services
                );

        services.clear();

        assertEquals(2, overview.services().size());
        assertThrows(
                UnsupportedOperationException.class,
                () -> overview.services().add(flask)
        );
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardOverviewResponse(
                        OBSERVED_AT,
                        availableMetrics(),
                        List.of(springBoot, springBoot)
                )
        );
    }

    @Test
    void required_fields_are_non_null() {
        assertThrows(
                NullPointerException.class,
                () -> new DashboardMetricSnapshot(
                        null,
                        null,
                        null
                )
        );
        assertThrows(
                NullPointerException.class,
                () -> new DashboardMetrics(
                        null,
                        availableMetric(),
                        availableMetric(),
                        availableMetric(),
                        availableMetric()
                )
        );
        assertThrows(
                NullPointerException.class,
                () -> new DashboardOverviewResponse(
                        null,
                        availableMetrics(),
                        List.of()
                )
        );
        assertThrows(
                NullPointerException.class,
                () -> new DashboardOverviewResponse(
                        OBSERVED_AT,
                        null,
                        List.of()
                )
        );
    }

    @Test
    void service_health_enforces_status_observation_rules() {
        DashboardServiceHealth up =
                new DashboardServiceHealth(
                        DashboardServiceName.SPRING_BOOT,
                        DashboardServiceStatus.UP,
                        OBSERVED_AT
                );
        DashboardServiceHealth unknown =
                new DashboardServiceHealth(
                        DashboardServiceName.FLASK,
                        DashboardServiceStatus.UNKNOWN,
                        null
                );

        assertEquals(DashboardServiceName.SPRING_BOOT, up.service());
        assertEquals(DashboardServiceStatus.UNKNOWN, unknown.status());
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardServiceHealth(
                        DashboardServiceName.MONGODB,
                        DashboardServiceStatus.UNKNOWN,
                        OBSERVED_AT
                )
        );
        assertThrows(
                IllegalArgumentException.class,
                () -> new DashboardServiceHealth(
                        DashboardServiceName.MONGODB,
                        DashboardServiceStatus.DOWN,
                        null
                )
        );
        assertThrows(
                NullPointerException.class,
                () -> new DashboardServiceHealth(
                        null,
                        DashboardServiceStatus.UP,
                        OBSERVED_AT
                )
        );
    }

    @Test
    void overview_serializes_and_deserializes_with_jackson() throws Exception {
        DashboardOverviewResponse overview =
                new DashboardOverviewResponse(
                        OBSERVED_AT,
                        availableMetrics(),
                        List.of(
                                new DashboardServiceHealth(
                                        DashboardServiceName.SPRING_BOOT,
                                        DashboardServiceStatus.UP,
                                        OBSERVED_AT
                                )
                        )
                );

        String json = objectMapper.writeValueAsString(overview);
        DashboardOverviewResponse restored =
                objectMapper.readValue(
                        json,
                        DashboardOverviewResponse.class
                );

        assertTrue(json.contains("\"events24h\""));
        assertTrue(json.contains("\"availability\":\"AVAILABLE\""));
        assertEquals(overview, restored);
        assertNotNull(restored.services());
        assertFalse(restored.services().isEmpty());
    }

    private static DashboardMetrics availableMetrics() {
        DashboardMetricSnapshot metric = availableMetric();

        return new DashboardMetrics(
                metric,
                metric,
                metric,
                metric,
                metric
        );
    }

    private static DashboardMetricSnapshot availableMetric() {
        return new DashboardMetricSnapshot(
                DashboardMetricAvailability.AVAILABLE,
                0L,
                OBSERVED_AT
        );
    }
}
