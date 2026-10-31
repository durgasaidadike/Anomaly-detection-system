package com.prism.backend.controller;

import com.prism.backend.dto.api.ApiResponseEnvelope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Health check controller demonstrating the REST API pattern.
 * <p>
 * This controller shows the established conventions:
 * - Extends BaseController for response building
 * - Uses standardized ApiResponseEnvelope
 * - Delegates to service layer (placeholder for demonstration)
 * - Returns structured API responses
 */
@RestController
@RequestMapping("/api/health")
public class HealthController extends BaseController {

    @GetMapping
    public ApiResponseEnvelope<Map<String, String>> health() {
        return success(
                "health-check",
                Map.of("status", "UP", "service", "prism-backend")
        );
    }
}
