package com.prism.backend.integration.flask;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;

public final class JavaHttpTransport implements DownstreamHttpTransport {

    private final HttpClient httpClient;

    public JavaHttpTransport(HttpClient httpClient) {
        this.httpClient = Objects.requireNonNull(
                httpClient,
                "httpClient must not be null"
        );
    }

    @Override
    public CompletableFuture<DownstreamHttpResponse> send(
            URI uri,
            Map<String, String> headers,
            String requestBody,
            Duration timeout
    ) {
        Objects.requireNonNull(uri, "uri must not be null");
        Objects.requireNonNull(headers, "headers must not be null");
        Objects.requireNonNull(requestBody, "requestBody must not be null");
        Objects.requireNonNull(timeout, "timeout must not be null");

        if (timeout.isZero() || timeout.isNegative()) {
            throw new IllegalArgumentException(
                    "timeout must be positive"
            );
        }

        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(uri)
                .timeout(timeout)
                .POST(
                        HttpRequest.BodyPublishers.ofString(
                                requestBody,
                                StandardCharsets.UTF_8
                        )
                );

        headers.forEach(builder::header);

        return httpClient
                .sendAsync(
                        builder.build(),
                        HttpResponse.BodyHandlers.ofString(
                                StandardCharsets.UTF_8
                        )
                )
                .thenApply(response ->
                        new DownstreamHttpResponse(
                                response.statusCode(),
                                response.body()
                        )
                );
    }
}
