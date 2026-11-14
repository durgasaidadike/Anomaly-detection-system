package com.prism.backend.configuration;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class ApiConfigurationPropertiesTest {

    @Test
    void propertiesCanBeInstantiated() {
        ApiConfigurationProperties properties =
                new ApiConfigurationProperties(8080, true);

        assertNotNull(properties);
        assertEquals(8080, properties.port());
        assertEquals(true, properties.actuatorEnabled());
    }
}
