package com.prism.backend.dto.api;

import java.time.Instant;

public record ApiRequestEnvelope<T>(
        String requestId,
        Instant timestamp,
        String sessionId,
        String userId,
        String projectId,
        T payload
) {
}
