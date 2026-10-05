package com.prism.backend.integration.flask;

import java.net.URI;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

public interface DownstreamHttpTransport {

    CompletableFuture<DownstreamHttpResponse> send(
            URI uri,
            Map<String, String> headers,
            String requestBody,
            Duration timeout
    );
}
