package com.prism.backend.dto.api;

import java.time.Instant;
import java.util.List;

public record ApiResponseEnvelope<T>(
        String status,
        Instant timestamp,
        String requestId,
        String processingTime,
        T data,
        List<ApiError> errors
) {

    public ApiResponseEnvelope {
        errors = errors == null
                ? List.of()
                : List.copyOf(errors);
    }
}
