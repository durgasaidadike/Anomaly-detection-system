package com.prism.backend.integration.resilience;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class FailoverCoordinatorContractTest {

    @Test
    void coordinatorImplementsFailoverCoordinatorInterface() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        FailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        assertTrue(
                coordinator instanceof FailoverCoordinator,
                "DefaultFailoverCoordinator must implement FailoverCoordinator"
        );
    }

    @Test
    void coordinateMethodSignatureMatchesContract() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.DO_NOT_FAILOVER);

        FailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-901",
                        "correlation-901",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.NEVER,
                        null,
                        "trace-901"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-901",
                        "attempt-901",
                        "correlation-901",
                        Map.of("test", "data")
                );

        CompletableFuture<FailoverCoordinationResult> result =
                coordinator.coordinate(context, failure, request);

        assertNotNull(
                result,
                "coordinate must return a CompletableFuture"
        );

        assertTrue(
                result.isDone(),
                "Returned CompletableFuture should be completable"
        );

        FailoverCoordinationResult coordinationResult =
                result.join();

        assertNotNull(
                coordinationResult,
                "CompletableFuture must complete with a FailoverCoordinationResult"
        );

        assertTrue(
                coordinationResult instanceof FailoverCoordinationResult,
                "Result must be of type FailoverCoordinationResult"
        );
    }

    @Test
    void coordinateAcceptsFailoverContext() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.DO_NOT_FAILOVER);

        FailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-902",
                        "correlation-902",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.NEVER,
                        null,
                        "trace-902"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-902",
                        "attempt-902",
                        "correlation-902",
                        Map.of("test", "data")
                );

        assertDoesNotThrow(
                () -> coordinator.coordinate(context, failure, request).join(),
                "coordinate must accept FailoverContext as first parameter"
        );
    }

    @Test
    void coordinateAcceptsDownstreamFailure() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.DO_NOT_FAILOVER);

        FailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-903",
                        "correlation-903",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.NEVER,
                        null,
                        "trace-903"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-903",
                        "attempt-903",
                        "correlation-903",
                        Map.of("test", "data")
                );

        assertDoesNotThrow(
                () -> coordinator.coordinate(context, failure, request).join(),
                "coordinate must accept DownstreamFailure as second parameter"
        );
    }

    @Test
    void coordinateAcceptsFailoverInvocationRequest() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.DO_NOT_FAILOVER);

        FailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-904",
                        "correlation-904",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.NEVER,
                        null,
                        "trace-904"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-904",
                        "attempt-904",
                        "correlation-904",
                        Map.of("test", "data")
                );

        assertDoesNotThrow(
                () -> coordinator.coordinate(context, failure, request).join(),
                "coordinate must accept FailoverInvocationRequest as third parameter"
        );
    }

    @Test
    void coordinateReturnsCompletableFutureOfFailoverCoordinationResult() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.DO_NOT_FAILOVER);

        FailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-905",
                        "correlation-905",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.NEVER,
                        null,
                        "trace-905"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-905",
                        "attempt-905",
                        "correlation-905",
                        Map.of("test", "data")
                );

        CompletableFuture<FailoverCoordinationResult> result =
                coordinator.coordinate(context, failure, request);

        assertTrue(
                result instanceof CompletableFuture,
                "coordinate must return CompletableFuture"
        );

        FailoverCoordinationResult coordinationResult =
                result.join();

        assertTrue(
                coordinationResult instanceof FailoverCoordinationResult,
                "CompletableFuture must contain FailoverCoordinationResult"
        );
    }
}
