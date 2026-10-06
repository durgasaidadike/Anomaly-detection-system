package com.prism.backend.integration.resilience;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;

import java.net.URI;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class FailoverCoordinatorTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void doesNotInvokeWhenPolicyRejectsFailover() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.DO_NOT_FAILOVER);

        DefaultFailoverCoordinator coordinator =
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

        assertTrue(result.isDone());

        FailoverCoordinationResult coordinationResult =
                result.join();

        assertEquals(
                FailoverCoordinationStatus.FAILOVER_NOT_ALLOWED,
                coordinationResult.status()
        );

        assertFalse(coordinationResult.responseOptional().isPresent());

        verify(policy, times(1)).evaluate(failure);
        verify(resolver, never()).resolve(any());
        verify(invoker, never()).invoke(any(), any());
    }

    @Test
    void returnsNoTargetWhenResolutionProducesNoTarget() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.FAILOVER_ALLOWED);

        when(resolver.resolve(any(FailoverContext.class)))
                .thenReturn(Optional.empty());

        DefaultFailoverCoordinator coordinator =
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
                        FailoverDisposition.CONDITIONAL,
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

        CompletableFuture<FailoverCoordinationResult> result =
                coordinator.coordinate(context, failure, request);

        assertTrue(result.isDone());

        FailoverCoordinationResult coordinationResult =
                result.join();

        assertEquals(
                FailoverCoordinationStatus.NO_TARGET,
                coordinationResult.status()
        );

        assertFalse(coordinationResult.responseOptional().isPresent());

        verify(policy, times(1)).evaluate(failure);
        verify(resolver, times(1)).resolve(context);
        verify(invoker, never()).invoke(any(), any());
    }

    @Test
    void invokesResolvedTarget() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.FAILOVER_ALLOWED);

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        when(resolver.resolve(any(FailoverContext.class)))
                .thenReturn(Optional.of(target));

        ObjectNode responseNode = objectMapper.createObjectNode();
        responseNode.put("status", "ok");

        FailoverInvocationResponse response =
                new FailoverInvocationResponse(
                        200,
                        responseNode
                );

        when(invoker.invoke(any(FailoverTarget.class), any(FailoverInvocationRequest.class)))
                .thenReturn(CompletableFuture.completedFuture(response));

        DefaultFailoverCoordinator coordinator =
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
                        FailoverDisposition.CONDITIONAL,
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

        CompletableFuture<FailoverCoordinationResult> result =
                coordinator.coordinate(context, failure, request);

        assertTrue(result.isDone());

        FailoverCoordinationResult coordinationResult =
                result.join();

        assertEquals(
                FailoverCoordinationStatus.INVOKED,
                coordinationResult.status()
        );

        assertTrue(coordinationResult.responseOptional().isPresent());

        assertEquals(
                response,
                coordinationResult.responseOptional().get()
        );

        verify(policy, times(1)).evaluate(failure);
        verify(resolver, times(1)).resolve(context);
        verify(invoker, times(1)).invoke(target, request);
    }

    @Test
    void contextReachesResolverUnchanged() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.FAILOVER_ALLOWED);

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        when(resolver.resolve(any(FailoverContext.class)))
                .thenReturn(Optional.of(target));

        ObjectNode responseNode = objectMapper.createObjectNode();
        responseNode.put("status", "ok");

        FailoverInvocationResponse response =
                new FailoverInvocationResponse(
                        200,
                        responseNode
                );

        when(invoker.invoke(any(FailoverTarget.class), any(FailoverInvocationRequest.class)))
                .thenReturn(CompletableFuture.completedFuture(response));

        DefaultFailoverCoordinator coordinator =
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
                        FailoverDisposition.CONDITIONAL,
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

        coordinator.coordinate(context, failure, request).join();

        verify(resolver).resolve(argThat(resolvedContext ->
                resolvedContext.operationRequestId().equals("operation-904") &&
                resolvedContext.correlationId().equals("correlation-904") &&
                resolvedContext.failedServiceName().equals("flask-primary")
        ));
    }

    @Test
    void requestReachesInvokerUnchanged() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.FAILOVER_ALLOWED);

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        when(resolver.resolve(any(FailoverContext.class)))
                .thenReturn(Optional.of(target));

        ObjectNode responseNode = objectMapper.createObjectNode();
        responseNode.put("status", "ok");

        FailoverInvocationResponse response =
                new FailoverInvocationResponse(
                        200,
                        responseNode
                );

        when(invoker.invoke(any(FailoverTarget.class), any(FailoverInvocationRequest.class)))
                .thenReturn(CompletableFuture.completedFuture(response));

        DefaultFailoverCoordinator coordinator =
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
                        FailoverDisposition.CONDITIONAL,
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

        coordinator.coordinate(context, failure, request).join();

        verify(invoker).invoke(eq(target), argThat(invokedRequest ->
                invokedRequest.operationRequestId().equals("operation-905") &&
                invokedRequest.attemptRequestId().equals("attempt-905") &&
                invokedRequest.correlationId().equals("correlation-905") &&
                invokedRequest.payload().equals(Map.of("test", "data"))
        ));
    }

    @Test
    void nullDependenciesRejected() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        assertThrows(
                NullPointerException.class,
                () -> new DefaultFailoverCoordinator(
                        null,
                        resolver,
                        invoker
                )
        );

        assertThrows(
                NullPointerException.class,
                () -> new DefaultFailoverCoordinator(
                        policy,
                        null,
                        invoker
                )
        );

        assertThrows(
                NullPointerException.class,
                () -> new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        null
                )
        );
    }

    @Test
    void nullInvocationArgumentsRejected() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        DefaultFailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-906",
                        "correlation-906",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-906"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-906",
                        "attempt-906",
                        "correlation-906",
                        Map.of("test", "data")
                );

        assertThrows(
                NullPointerException.class,
                () -> coordinator.coordinate(null, failure, request)
        );

        assertThrows(
                NullPointerException.class,
                () -> coordinator.coordinate(context, null, request)
        );

        assertThrows(
                NullPointerException.class,
                () -> coordinator.coordinate(context, failure, null)
        );
    }

    @Test
    void invocationFailureIsPreserved() {

        FailoverPolicy policy = mock(FailoverPolicy.class);
        FailoverTargetResolver resolver = mock(FailoverTargetResolver.class);
        FailoverInvoker invoker = mock(FailoverInvoker.class);

        when(policy.evaluate(any(DownstreamFailure.class)))
                .thenReturn(FailoverDecision.FAILOVER_ALLOWED);

        FailoverTarget target =
                new FailoverTarget(
                        "flask-backup",
                        URI.create("http://127.0.0.1:5001")
                );

        when(resolver.resolve(any(FailoverContext.class)))
                .thenReturn(Optional.of(target));

        RuntimeException exception =
                new RuntimeException("Invocation failed");

        when(invoker.invoke(any(FailoverTarget.class), any(FailoverInvocationRequest.class)))
                .thenReturn(CompletableFuture.failedFuture(exception));

        DefaultFailoverCoordinator coordinator =
                new DefaultFailoverCoordinator(
                        policy,
                        resolver,
                        invoker
                );

        FailoverContext context =
                new FailoverContext(
                        "operation-907",
                        "correlation-907",
                        "flask-primary"
                );

        DownstreamFailure failure =
                new DownstreamFailure(
                        "flask-primary",
                        DownstreamFailureKind.TIMEOUT,
                        RetryDisposition.CONDITIONAL,
                        FailoverDisposition.CONDITIONAL,
                        null,
                        "trace-907"
                );

        FailoverInvocationRequest request =
                new FailoverInvocationRequest(
                        "operation-907",
                        "attempt-907",
                        "correlation-907",
                        Map.of("test", "data")
                );

        CompletableFuture<FailoverCoordinationResult> result =
                coordinator.coordinate(context, failure, request);

        assertTrue(result.isCompletedExceptionally());

        result.handle((r, ex) -> {
            assertSame(exception, ex.getCause());
            return null;
        }).join();

        verify(policy, times(1)).evaluate(failure);
        verify(resolver, times(1)).resolve(context);
        verify(invoker, times(1)).invoke(target, request);
    }
}
