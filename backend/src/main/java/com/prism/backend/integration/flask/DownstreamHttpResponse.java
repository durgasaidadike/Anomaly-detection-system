package com.prism.backend.integration.flask;

public record DownstreamHttpResponse(
        int statusCode,
        String body
) {
}
