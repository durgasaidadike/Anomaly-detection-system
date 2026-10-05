package com.prism.backend.integration.flask;

import com.fasterxml.jackson.databind.JsonNode;
import com.prism.backend.dto.api.ApiRequestEnvelope;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

public interface FlaskGatewayPort {

    CompletableFuture<JsonNode> analyzeEvent(
            ApiRequestEnvelope<Map<String, Object>> request,
            String correlationId
    );
}
