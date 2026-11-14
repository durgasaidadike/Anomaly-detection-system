package com.prism.backend.configuration;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.net.URI;
import java.time.Duration;
import java.util.Objects;

/**
 * Flask service configuration properties for PRISM backend.
 * <p>
 * These properties control the Flask integration without modifying
 * the sealed Flask client or transport contracts.
 * External configuration through environment variables is supported.
 */
@Validated
@ConfigurationProperties(prefix = "prism.flask")
public record FlaskServiceConfigurationProperties(

        @NotBlank
        String serviceName,

        @NotNull
        @Pattern(regexp = "^https?://.*", message = "must be a valid HTTP or HTTPS URL")
        String baseUri,

        @NotNull
        Duration timeout
) {

    public FlaskServiceConfigurationProperties {
        Objects.requireNonNull(serviceName, "serviceName must not be null");

        if (serviceName.isBlank()) {
            throw new IllegalArgumentException("serviceName must not be blank");
        }

        Objects.requireNonNull(baseUri, "baseUri must not be null");

        if (!baseUri.matches("^https?://.*")) {
            throw new IllegalArgumentException("baseUri must be a valid HTTP or HTTPS URL");
        }

        Objects.requireNonNull(timeout, "timeout must not be null");
    }
}
