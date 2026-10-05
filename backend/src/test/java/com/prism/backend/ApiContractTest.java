package com.prism.backend;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.prism.backend.dto.api.ApiError;
import com.prism.backend.dto.api.ApiRequestEnvelope;
import com.prism.backend.dto.api.ApiResponseEnvelope;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ApiContractTest {

    private final ObjectMapper objectMapper =
            new ObjectMapper()
                    .registerModule(new JavaTimeModule());

    @Test
    void request_envelope_contains_defined_contract_fields() throws Exception {
        Instant timestamp =
                Instant.parse("2026-10-05T07:00:00Z");

        ApiRequestEnvelope<String> request =
                new ApiRequestEnvelope<>(
                        "req-001",
                        timestamp,
                        "session-001",
                        "user-001",
                        "project-001",
                        "payload"
                );

        String json = objectMapper.writeValueAsString(request);

        assertTrue(json.contains("\"requestId\":\"req-001\""));
        assertTrue(json.contains("\"timestamp\""));
        assertTrue(json.contains("\"sessionId\":\"session-001\""));
        assertTrue(json.contains("\"userId\":\"user-001\""));
        assertTrue(json.contains("\"projectId\":\"project-001\""));
        assertTrue(json.contains("\"payload\":\"payload\""));
    }

    @Test
    void response_envelope_contains_defined_contract_fields() throws Exception {
        Instant timestamp =
                Instant.parse("2026-10-05T07:00:00Z");

        ApiResponseEnvelope<String> response =
                new ApiResponseEnvelope<>(
                        "SUCCESS",
                        timestamp,
                        "req-001",
                        "15ms",
                        "result",
                        List.of()
                );

        String json = objectMapper.writeValueAsString(response);

        assertTrue(json.contains("\"status\":\"SUCCESS\""));
        assertTrue(json.contains("\"timestamp\""));
        assertTrue(json.contains("\"requestId\":\"req-001\""));
        assertTrue(json.contains("\"processingTime\":\"15ms\""));
        assertTrue(json.contains("\"data\":\"result\""));
        assertTrue(json.contains("\"errors\":[]"));
    }

    @Test
    void api_error_contains_all_defined_failure_fields() throws Exception {
        ApiError error =
                new ApiError(
                        "FLASK_TIMEOUT",
                        "Intelligence service timed out.",
                        "Retry the operation.",
                        "trace-001"
                );

        String json = objectMapper.writeValueAsString(error);

        assertTrue(json.contains("\"errorCode\":\"FLASK_TIMEOUT\""));
        assertTrue(json.contains("\"errorMessage\":\"Intelligence service timed out.\""));
        assertTrue(json.contains("\"suggestedAction\":\"Retry the operation.\""));
        assertTrue(json.contains("\"traceIdentifier\":\"trace-001\""));
    }

    @Test
    void response_normalizes_null_error_list_to_empty_list() {
        ApiResponseEnvelope<String> response =
                new ApiResponseEnvelope<>(
                        "SUCCESS",
                        Instant.now(),
                        "req-001",
                        "10ms",
                        "result",
                        null
                );

        assertNotNull(response.errors());
        assertTrue(response.errors().isEmpty());
    }

    @Test
    void response_error_list_is_immutable() {
        ApiError error =
                new ApiError(
                        "ERR",
                        "message",
                        "action",
                        "trace"
                );

        ApiResponseEnvelope<String> response =
                new ApiResponseEnvelope<>(
                        "FAILURE",
                        Instant.now(),
                        "req-001",
                        "10ms",
                        null,
                        List.of(error)
                );

        assertThrows(
                UnsupportedOperationException.class,
                () -> response.errors().add(error)
        );
    }
}
