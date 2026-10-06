package com.prism.backend.integration.resilience;

import java.util.concurrent.CompletableFuture;

public interface FailoverCoordinator {

    CompletableFuture<FailoverCoordinationResult> coordinate(
            FailoverContext context,
            DownstreamFailure failure,
            FailoverInvocationRequest request
    );
}
