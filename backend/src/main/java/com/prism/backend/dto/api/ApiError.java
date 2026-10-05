package com.prism.backend.dto.api;

public record ApiError(
        String errorCode,
        String errorMessage,
        String suggestedAction,
        String traceIdentifier
) {
}
