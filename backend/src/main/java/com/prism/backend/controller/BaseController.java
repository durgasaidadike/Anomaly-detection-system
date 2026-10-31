package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiError;
import com.prism.backend.dto.api.ApiResponseEnvelope;

import java.time.Instant;
import java.util.List;

/**
 * Base controller establishing REST API conventions for PRISM.
 * <p>
 * All controllers must:
 * - Receive HTTP requests
 * - Validate incoming request data
 * - Delegate business operations to services
 * - Return standardized API responses
 * - Not contain business logic
 */
public abstract class BaseController {

    protected static final long DEFAULT_PROCESSING_TIME_MS = 0L;

    protected <T> ApiResponseEnvelope<T> success(
            String requestId,
            T data
    ) {
        return new ApiResponseEnvelope<>(
                "SUCCESS",
                Instant.now(),
                requestId,
                String.valueOf(DEFAULT_PROCESSING_TIME_MS),
                data,
                List.of()
        );
    }

    protected <T> ApiResponseEnvelope<T> error(
            String requestId,
            ApiError error
    ) {
        return new ApiResponseEnvelope<>(
                "ERROR",
                Instant.now(),
                requestId,
                String.valueOf(DEFAULT_PROCESSING_TIME_MS),
                null,
                List.of(error)
        );
    }

    protected <T> ApiResponseEnvelope<T> error(
            String requestId,
            List<ApiError> errors
    ) {
        return new ApiResponseEnvelope<>(
                "ERROR",
                Instant.now(),
                requestId,
                String.valueOf(DEFAULT_PROCESSING_TIME_MS),
                null,
                errors
        );
    }
}
