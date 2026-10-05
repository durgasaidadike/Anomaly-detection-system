package com.prism.backend.integration.resilience;

import java.util.Objects;
import java.util.Optional;

public final class ConfiguredFailoverTargetResolver
        implements FailoverTargetResolver {

    private final FailoverTarget target;

    public ConfiguredFailoverTargetResolver(
            FailoverTarget target
    ) {
        this.target = Objects.requireNonNull(
                target,
                "target must not be null"
        );
    }

    @Override
    public Optional<FailoverTarget> resolve(
            FailoverContext context
    ) {
        Objects.requireNonNull(
                context,
                "context must not be null"
        );

        return Optional.of(target);
    }
}
