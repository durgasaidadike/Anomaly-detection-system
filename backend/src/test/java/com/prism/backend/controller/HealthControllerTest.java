package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiResponseEnvelope;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class HealthControllerTest {

    @Test
    void healthEndpointReturnsStructuredResponse() {
        HealthController controller = new HealthController();

        ApiResponseEnvelope<Map<String, String>> response = controller.health();

        assertEquals("SUCCESS", response.status());
        assertNotNull(response.requestId());
        assertNotNull(response.timestamp());
        assertEquals("0", response.processingTime());
        assertEquals(Map.of("status", "UP", "service", "prism-backend"), response.data());
        assertTrue(response.errors().isEmpty());
    }
}
