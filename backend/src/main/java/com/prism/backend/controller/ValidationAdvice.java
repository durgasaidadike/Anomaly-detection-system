package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiError;
import com.prism.backend.dto.api.ApiResponseEnvelope;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Global exception handler for request validation failures.
 * <p>
 * Converts validation exceptions into standardized API error responses.
 */
@RestControllerAdvice
public class ValidationAdvice {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponseEnvelope<Void>> handleValidationException(
            MethodArgumentNotValidException ex
    ) {
        List<ApiError> errors = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error -> new ApiError(
                        "VALIDATION_ERROR",
                        error.getDefaultMessage(),
                        "Correct the request and retry",
                        UUID.randomUUID().toString()
                ))
                .collect(Collectors.toList());

        ApiResponseEnvelope<Void> response = new ApiResponseEnvelope<>(
                "VALIDATION_ERROR",
                java.time.Instant.now(),
                UUID.randomUUID().toString(),
                "0",
                null,
                errors
        );

        return ResponseEntity.badRequest().body(response);
    }
}
