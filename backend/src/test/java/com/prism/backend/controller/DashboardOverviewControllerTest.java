package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiResponseEnvelope;
import com.prism.backend.dto.dashboard.DashboardOverviewResponse;
import com.prism.backend.service.dashboard.DashboardOverviewService;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

class DashboardOverviewControllerTest {

    @Test
    void returnsStandardResponseEnvelope() {
        DashboardOverviewController controller =
                new DashboardOverviewController(
                        new DashboardOverviewService()
                );

        ApiResponseEnvelope<DashboardOverviewResponse> response =
                controller.getOverview("request-123");

        assertEquals("SUCCESS", response.status());
        assertEquals("request-123", response.requestId());
        assertNotNull(response.timestamp());
        assertNotNull(response.data());
        assertTrue(response.errors().isEmpty());
    }

    @Test
    void generatesRequestIdWhenHeaderIsMissing() {
        DashboardOverviewController controller =
                new DashboardOverviewController(
                        new DashboardOverviewService()
                );

        ApiResponseEnvelope<DashboardOverviewResponse> response =
                controller.getOverview(null);

        assertNotNull(response.requestId());
        assertDoesNotThrow(
                () -> UUID.fromString(response.requestId())
        );
    }

    @Test
    void delegatesOverviewRetrievalToService() {
        DashboardOverviewService service =
                mock(DashboardOverviewService.class);
        DashboardOverviewController controller =
                new DashboardOverviewController(service);

        controller.getOverview("request-456");

        verify(service, times(1)).getOverview();
    }
}
