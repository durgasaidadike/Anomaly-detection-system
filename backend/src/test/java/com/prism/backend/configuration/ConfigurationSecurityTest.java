package com.prism.backend.configuration;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ConfigurationSecurityTest {

    @Test
    void apiConfigurationToStringDoesNotExposeSecrets() {
        ApiConfigurationProperties properties =
                new ApiConfigurationProperties(8080, true);

        String toString = properties.toString();

        assertFalse(toString.contains("password"));
        assertFalse(toString.contains("secret"));
        assertFalse(toString.contains("token"));
        assertFalse(toString.contains("credential"));
    }

    @Test
    void flaskConfigurationToStringDoesNotExposeSecrets() {
        FlaskServiceConfigurationProperties properties =
                new FlaskServiceConfigurationProperties(
                        "flask-gateway",
                        "http://localhost:5000",
                        Duration.ofSeconds(30)
                );

        String toString = properties.toString();

        assertFalse(toString.contains("password"));
        assertFalse(toString.contains("secret"));
        assertFalse(toString.contains("token"));
        assertFalse(toString.contains("credential"));
    }

    @Test
    void configurationRecordsDoNotHaveSecretFields() {
        ApiConfigurationProperties apiConfig =
                new ApiConfigurationProperties(8080, true);

        FlaskServiceConfigurationProperties flaskConfig =
                new FlaskServiceConfigurationProperties(
                        "flask-gateway",
                        "http://localhost:5000",
                        Duration.ofSeconds(30)
                );

        assertEquals(8080, apiConfig.port());
        assertEquals(true, apiConfig.actuatorEnabled());

        assertEquals("flask-gateway", flaskConfig.serviceName());
        assertEquals("http://localhost:5000", flaskConfig.baseUri());
        assertEquals(Duration.ofSeconds(30), flaskConfig.timeout());

        assertTrue(apiConfig.getClass().isRecord());
        assertTrue(flaskConfig.getClass().isRecord());
    }
}
