package com.prism.backend.security;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "prism.jwt")
public record PrismJwtProperties(
        String issuerUri,
        String rolesClaim
) {

    public PrismJwtProperties {
        rolesClaim = rolesClaim == null || rolesClaim.isBlank()
                ? "roles"
                : rolesClaim;
    }
}
