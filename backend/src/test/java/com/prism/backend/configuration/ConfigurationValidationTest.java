package com.prism.backend.configuration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

@SpringBootTest(classes = ConfigurationBootstrap.class)
@TestPropertySource(properties = {
        "prism.api.port=8080",
        "prism.api.actuator-enabled=true",
        "prism.flask.service-name=flask-gateway",
        "prism.flask.base-uri=http://localhost:5000",
        "prism.flask.timeout=30s"
})
class ConfigurationValidationTest {

    @Autowired(required = false)
    private ApiConfigurationProperties apiConfigurationProperties;

    @Autowired(required = false)
    private FlaskServiceConfigurationProperties flaskServiceConfigurationProperties;

    @Test
    void validConfigurationSucceeds() {
        assertNotNull(apiConfigurationProperties);
        assertNotNull(flaskServiceConfigurationProperties);
    }

    @Test
    void nullPortIsRejected() {
        assertThrows(RuntimeException.class, () ->
                new ApiConfigurationProperties(null, true)
        );
    }

    @Test
    void invalidPortIsRejected() {
        assertThrows(IllegalArgumentException.class, () ->
                new ApiConfigurationProperties(0, true)
        );
    }

    @Test
    void blankServiceNameIsRejected() {
        assertThrows(RuntimeException.class, () ->
                new FlaskServiceConfigurationProperties("", "http://localhost:5000", Duration.ofSeconds(30))
        );
    }

    @Test
    void invalidUriIsRejected() {
        assertThrows(IllegalArgumentException.class, () ->
                new FlaskServiceConfigurationProperties("flask", "ftp://localhost:5000", Duration.ofSeconds(30))
        );
    }

    @Test
    void nullUriIsRejected() {
        assertThrows(RuntimeException.class, () ->
                new FlaskServiceConfigurationProperties("flask", null, Duration.ofSeconds(30))
        );
    }
}
