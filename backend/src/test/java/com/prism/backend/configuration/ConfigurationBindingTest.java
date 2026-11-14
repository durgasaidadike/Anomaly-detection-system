package com.prism.backend.configuration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

@SpringBootTest(classes = ConfigurationBootstrap.class)
@TestPropertySource(properties = {
        "prism.api.port=9090",
        "prism.api.actuator-enabled=false",
        "prism.flask.service-name=test-flask",
        "prism.flask.base-uri=http://test.example.com:6000",
        "prism.flask.timeout=60s"
})
class ConfigurationBindingTest {

    @Autowired
    private ApiConfigurationProperties apiConfigurationProperties;

    @Autowired
    private FlaskServiceConfigurationProperties flaskServiceConfigurationProperties;

    @Test
    void apiConfigurationPropertiesBindCorrectly() {
        assertNotNull(apiConfigurationProperties);
        assertEquals(9090, apiConfigurationProperties.port());
        assertEquals(false, apiConfigurationProperties.actuatorEnabled());
    }

    @Test
    void flaskServiceConfigurationPropertiesBindCorrectly() {
        assertNotNull(flaskServiceConfigurationProperties);
        assertEquals("test-flask", flaskServiceConfigurationProperties.serviceName());
        assertEquals("http://test.example.com:6000", flaskServiceConfigurationProperties.baseUri());
        assertEquals(Duration.ofSeconds(60), flaskServiceConfigurationProperties.timeout());
    }
}
