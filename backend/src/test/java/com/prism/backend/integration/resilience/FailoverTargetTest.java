package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import java.net.URI;

import static org.junit.jupiter.api.Assertions.*;

class FailoverTargetTest {

    @Test
    void validHttpTarget() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        assertEquals(
                "flask-backup",
                target.serviceName()
        );

        assertEquals(
                URI.create("http://127.0.0.1:5001"),
                target.endpoint()
        );
    }

    @Test
    void validHttpsTarget() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("https://backup.example.com")
                );

        assertEquals(
                "flask-backup",
                target.serviceName()
        );

        assertEquals(
                URI.create("https://backup.example.com"),
                target.endpoint()
        );
    }

    @Test
    void nullServiceName() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverTarget(
                        null,
                        URI.create("http://127.0.0.1:5001")
                )
        );
    }

    @Test
    void blankServiceName() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverTarget(
                        " ",
                        URI.create("http://127.0.0.1:5001")
                )
        );
    }

    @Test
    void nullEndpoint() {

        assertThrows(
                NullPointerException.class,
                () -> new FailoverTarget(
                        "flask-backup",
                        null
                )
        );
    }

    @Test
    void unsupportedScheme() {

        assertThrows(
                IllegalArgumentException.class,
                () -> new FailoverTarget(
                        "flask-backup",
                        URI.create("ftp://127.0.0.1:5001")
                )
        );
    }
}
