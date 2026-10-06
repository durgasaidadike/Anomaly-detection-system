package com.prism.backend.integration.resilience;

public enum FailoverCoordinationStatus {

    FAILOVER_NOT_ALLOWED,

    NO_TARGET,

    INVOKED
}
