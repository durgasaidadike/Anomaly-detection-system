package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;

import java.net.URI;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

class FailoverTargetResolverContractTest {

    @Test
    void resolverAcceptsFailoverContext() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        FailoverContext context =
                new FailoverContext(
                        "operation-901",
                        "correlation-901",
                        "flask-primary"
                );

        Optional<FailoverTarget> result =
                resolver.resolve(context);

        assertTrue(result.isPresent());
    }

    @Test
    void resolverReturnsOptionalFailoverTarget() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        FailoverContext context =
                new FailoverContext(
                        "operation-902",
                        "correlation-902",
                        "flask-primary"
                );

        Optional<FailoverTarget> result =
                resolver.resolve(context);

        assertTrue(result.isPresent());
        assertTrue(result.get() instanceof FailoverTarget);
    }

    @Test
    void resolverDoesNotCreateImplicitInfrastructure() {

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        FailoverTargetResolver resolver =
                new ConfiguredFailoverTargetResolver(target);

        FailoverContext context =
                new FailoverContext(
                        "operation-903",
                        "correlation-903",
                        "flask-primary"
                );

        Optional<FailoverTarget> result =
                resolver.resolve(context);

        assertTrue(result.isPresent());

        assertSame(
                target,
                result.get(),
                "Resolver must return the configured target, not create a new one"
        );
    }
}
