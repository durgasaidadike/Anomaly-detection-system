package com.prism.backend.integration.resilience;

import java.util.concurrent.CompletableFuture;

public interface FailoverInvoker {

    CompletableFuture<FailoverInvocationResponse> invoke(
            FailoverTarget target,
            FailoverInvocationRequest request
    );
}
