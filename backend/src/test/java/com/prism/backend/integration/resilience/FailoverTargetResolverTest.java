package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class FailoverTargetResolverTest {

    @Test
    void validResolution() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        ConfiguredFailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        FailoverContext context =
                new FailoverContext(
                        "operation-801",
                        "correlation-801",
                        "flask-primary"
                );

        Optional<FailoverTarget> result =
                resolver.resolve(context);

        assertTrue(result.isPresent());

        assertEquals(
                target,
                result.get()
        );
    }

    @Test
    void sameTargetReturned() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        ConfiguredFailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        FailoverContext context1 =
                new FailoverContext(
                        "operation-802",
                        "correlation-802",
                        "flask-primary"
                );

        FailoverContext context2 =
                new FailoverContext(
                        "operation-803",
                        "correlation-803",
                        "flask-primary"
                );

        Optional<FailoverTarget> result1 =
                resolver.resolve(context1);

        Optional<FailoverTarget> result2 =
                resolver.resolve(context2);

        assertTrue(result1.isPresent());
        assertTrue(result2.isPresent());

        assertSame(
                target,
                result1.get()
        );

        assertSame(
                target,
                result2.get()
        );
    }

    @Test
    void nullContext() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        ConfiguredFailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        assertThrows(
                NullPointerException.class,
                () -> resolver.resolve(null)
        );
    }

    @Test
    void nullTargetRejected() {

        assertThrows(
                NullPointerException.class,
                () -> new ConfiguredFailoverTargetResolver(null)
        );
    }

    @Test
    void contextIdentityPreserved() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        ConfiguredFailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        FailoverContext context =
                new FailoverContext(
                        "operation-804",
                        "correlation-804",
                        "flask-primary"
                );

        Optional<FailoverTarget> result =
                resolver.resolve(context);

        assertTrue(result.isPresent());

        assertEquals(
                "flask-backup",
                result.get().serviceName()
        );

        assertEquals(
                URI.create("http://127.0.0.1:5001"),
                result.get().endpoint()
        );
    }
}
