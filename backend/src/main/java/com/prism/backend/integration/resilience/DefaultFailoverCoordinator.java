package com.prism.backend.integration.resilience;

import java.util.Objects;
import java.util.concurrent.CompletableFuture;

public final class DefaultFailoverCoordinator
        implements FailoverCoordinator {

    private final FailoverPolicy failoverPolicy;
    private final FailoverTargetResolver targetResolver;
    private final FailoverInvoker failoverInvoker;

    public DefaultFailoverCoordinator(
            FailoverPolicy failoverPolicy,
            FailoverTargetResolver targetResolver,
            FailoverInvoker failoverInvoker
    ) {
        this.failoverPolicy = Objects.requireNonNull(
                failoverPolicy,
                "failoverPolicy must not be null"
        );

        this.targetResolver = Objects.requireNonNull(
                targetResolver,
                "targetResolver must not be null"
        );

        this.failoverInvoker = Objects.requireNonNull(
                failoverInvoker,
                "failoverInvoker must not be null"
        );
    }

    @Override
    public CompletableFuture<FailoverCoordinationResult> coordinate(
            FailoverContext context,
            DownstreamFailure failure,
            FailoverInvocationRequest request
    ) {
        Objects.requireNonNull(
                context,
                "context must not be null"
        );

        Objects.requireNonNull(
                failure,
                "failure must not be null"
        );

        Objects.requireNonNull(
                request,
                "request must not be null"
        );

        FailoverDecision decision =
                failoverPolicy.evaluate(failure);

        if (decision
                == FailoverDecision.DO_NOT_FAILOVER) {

            return CompletableFuture.completedFuture(
                    new FailoverCoordinationResult(
                            FailoverCoordinationStatus.FAILOVER_NOT_ALLOWED,
                            null
                    )
            );
        }

        var target = targetResolver.resolve(context);

        if (target.isEmpty()) {
            return CompletableFuture.completedFuture(
                    new FailoverCoordinationResult(
                            FailoverCoordinationStatus.NO_TARGET,
                            null
                    )
            );
        }

        return failoverInvoker
                .invoke(target.get(), request)
                .thenApply(response ->
                        new FailoverCoordinationResult(
                                FailoverCoordinationStatus.INVOKED,
                                response
                        )
                );
    }
}
