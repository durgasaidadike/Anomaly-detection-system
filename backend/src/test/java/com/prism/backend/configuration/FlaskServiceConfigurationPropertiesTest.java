package com.prism.backend.configuration;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class FlaskServiceConfigurationPropertiesTest {

    @Test
    void propertiesCanBeInstantiated() {
        FlaskServiceConfigurationProperties properties =
                new FlaskServiceConfigurationProperties(
                        "flask-gateway",
                        "http://localhost:5000",
                        Duration.ofSeconds(30)
                );

        assertNotNull(properties);
        assertEquals("flask-gateway", properties.serviceName());
        assertEquals("http://localhost:5000", properties.baseUri());
        assertEquals(Duration.ofSeconds(30), properties.timeout());
    }
}
