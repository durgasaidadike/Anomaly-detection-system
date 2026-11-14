package com.prism.backend.configuration;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.util.Objects;

/**
 * API-level configuration properties for PRISM backend.
 * <p>
 * These properties control the HTTP server and API behavior.
 * External configuration through environment variables is supported.
 */
@Validated
@ConfigurationProperties(prefix = "prism.api")
public record ApiConfigurationProperties(

        @NotNull
        @Min(1)
        Integer port,

        @NotNull
        Boolean actuatorEnabled
) {

    public ApiConfigurationProperties {
        Objects.requireNonNull(port, "port must not be null");

        if (port < 1) {
            throw new IllegalArgumentException("port must be at least 1");
        }

        Objects.requireNonNull(actuatorEnabled, "actuatorEnabled must not be null");
    }
}
