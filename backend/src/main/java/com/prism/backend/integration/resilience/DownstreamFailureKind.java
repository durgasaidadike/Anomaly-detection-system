package com.prism.backend.integration.resilience;

public enum DownstreamFailureKind {

    TIMEOUT,
    CONNECTION_FAILURE,
    SERVICE_UNAVAILABLE,
    INVALID_RESPONSE,
    AUTHENTICATION_FAILURE,
    AUTHORIZATION_FAILURE,
    VALIDATION_FAILURE,
    PROTOCOL_FAILURE,
    UNKNOWN
}
