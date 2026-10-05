package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class FailoverInvocationRequestTest {

    @Test
    void validRequest() {

        Map<String, Object> payload =
                new LinkedHashMap<>();

        payload.put("key", "value");

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-601",
                        "attempt-601",
                        "correlation-601",
                        payload
                );

        assertEquals(
                "operation-601",
                request.operationRequestId()
        );

        assertEquals(
                "attempt-601",
                request.attemptRequestId()
        );

        assertEquals(
                "correlation-601",
                request.correlationId()
        );

        assertEquals(
                "value",
                request.payload().get("key")
        );
    }

    @Test
    void blankOperationRequestId() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverInvocationRequest(
                        " ",
                        "attempt-602",
                        "correlation-602",
                        Map.of()
                )
        );
    }

    @Test
    void blankAttemptRequestId() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverInvocationRequest(
                        "operation-603",
                        " ",
                        "correlation-603",
                        Map.of()
                )
        );
    }

    @Test
    void blankCorrelationId() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverInvocationRequest(
                        "operation-604",
                        "attempt-604",
                        " ",
                        Map.of()
                )
        );
    }

    @Test
    void nullPayload() {

        assertThrows(
                NullPointerException.class,
                () -> new FailoverInvocationRequest(
                        "operation-605",
                        "attempt-605",
                        "correlation-605",
                        null
                )
        );
    }

    @Test
    void payloadIsImmutable() {

        Map<String, Object> payload =
                new LinkedHashMap<>();

        payload.put("key", "value");

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-606",
                        "attempt-606",
                        "correlation-606",
                        payload
                );

        payload.put("newKey", "newValue");

        assertFalse(
                request.payload().containsKey("newKey")
        );
    }
}
