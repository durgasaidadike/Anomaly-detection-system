package com.prism.backend.integration.resilience;

import java.util.Optional;

public interface FailoverTargetResolver {

    Optional<FailoverTarget> resolve(
            FailoverContext context
    );
}
