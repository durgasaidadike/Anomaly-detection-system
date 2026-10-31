package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiError;
import com.prism.backend.dto.api.ApiResponseEnvelope;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class BaseControllerTest {

    private static class TestController extends BaseController {
    }

    @Test
    void successResponseBuildsCorrectEnvelope() {
        TestController controller = new TestController();

        ApiResponseEnvelope<Map<String, String>> response =
                controller.success("req-001", Map.of("key", "value"));

        assertEquals("SUCCESS", response.status());
        assertEquals("req-001", response.requestId());
        assertEquals("0", response.processingTime());
        assertNotNull(response.timestamp());
        assertEquals(Map.of("key", "value"), response.data());
        assertTrue(response.errors().isEmpty());
    }

    @Test
    void errorResponseWithSingleErrorBuildsCorrectEnvelope() {
        TestController controller = new TestController();

        ApiError error = new ApiError(
                "TEST_ERROR",
                "Test error message",
                "Retry",
                "trace-001"
        );

        ApiResponseEnvelope<Void> response =
                controller.error("req-002", error);

        assertEquals("ERROR", response.status());
        assertEquals("req-002", response.requestId());
        assertEquals("0", response.processingTime());
        assertNotNull(response.timestamp());
        assertEquals(1, response.errors().size());
        assertEquals(error, response.errors().get(0));
    }

    @Test
    void errorResponseWithMultipleErrorsBuildsCorrectEnvelope() {
        TestController controller = new TestController();

        List<ApiError> errors = List.of(
                new ApiError("ERROR_1", "Message 1", "Action 1", "trace-001"),
                new ApiError("ERROR_2", "Message 2", "Action 2", "trace-002")
        );

        ApiResponseEnvelope<Void> response =
                controller.error("req-003", errors);

        assertEquals("ERROR", response.status());
        assertEquals("req-003", response.requestId());
        assertEquals("0", response.processingTime());
        assertNotNull(response.timestamp());
        assertEquals(2, response.errors().size());
        assertEquals(errors, response.errors());
    }
}
