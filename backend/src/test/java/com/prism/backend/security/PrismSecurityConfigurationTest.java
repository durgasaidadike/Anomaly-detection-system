package com.prism.backend.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import java.time.Instant;
import java.util.List;

import static org.hamcrest.Matchers.containsString;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@Import(PrismSecurityConfigurationTest.TestJwtConfiguration.class)
@TestPropertySource(properties = "PRISM_JWT_ISSUER_URI=")
class PrismSecurityConfigurationTest {

    @Autowired
    private WebApplicationContext webApplicationContext;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
                .webAppContextSetup(webApplicationContext)
                .apply(springSecurity())
                .build();
    }

    @Test
    void health_endpoint_is_public() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("\"status\":\"SUCCESS\"")));
    }

    @Test
    void protected_api_request_requires_authentication() throws Exception {
        mockMvc.perform(get("/api/protected"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void invalid_bearer_token_is_rejected() throws Exception {
        mockMvc.perform(
                        get("/api/protected")
                                .header(
                                        "Authorization",
                                        "Bearer invalid-token"
                                )
                )
                .andExpect(status().isUnauthorized());
    }

    @Test
    void valid_jwt_authenticates_protected_api_request() throws Exception {
        mockMvc.perform(
                        get("/api/protected")
                                .with(jwt().jwt(jwt -> jwt
                                        .subject("user-001")
                                        .claim("roles", List.of("VIEWER"))
                                ))
                )
                .andExpect(status().isNotFound());
    }

    @Test
    void role_claims_and_scopes_are_mapped() {
        Jwt jwt = Jwt.withTokenValue("token")
                .header("alg", "none")
                .subject("user-001")
                .claim("roles", List.of(
                        "Administrator",
                        "SECURITY_ANALYST",
                        "Project Manager",
                        "ROLE_VIEWER",
                        "UNKNOWN",
                        " "
                ))
                .claim("scope", "read write")
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plusSeconds(300))
                .build();

        var authentication = PrismSecurityConfiguration
                .jwtAuthenticationConverter("roles")
                .convert(jwt);

        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("ROLE_ADMINISTRATOR")));
        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("ROLE_SECURITY_ANALYST")));
        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("ROLE_PROJECT_MANAGER")));
        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("ROLE_VIEWER")));
        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("SCOPE_read")));
        assertTrue(authentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("SCOPE_write")));

        Jwt customClaimJwt = Jwt.withTokenValue("token")
                .header("alg", "none")
                .claim("permissions", List.of("Viewer"))
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plusSeconds(300))
                .build();

        var customClaimAuthentication = PrismSecurityConfiguration
                .jwtAuthenticationConverter("permissions")
                .convert(customClaimJwt);

        assertTrue(customClaimAuthentication.getAuthorities().stream()
                .anyMatch(authority ->
                        authority.getAuthority().equals("ROLE_VIEWER")));
        assertTrue(customClaimAuthentication.getAuthorities().stream()
                .noneMatch(authority ->
                        authority.getAuthority().equals("ROLE_REPORTS")));
    }

    @Test
    void unrecognized_roles_do_not_grant_role_authorities() {
        Jwt jwt = Jwt.withTokenValue("token")
                .header("alg", "none")
                .claim("roles", List.of("ROOT", "", "ROLE_ROOT"))
                .issuedAt(Instant.now())
                .expiresAt(Instant.now().plusSeconds(300))
                .build();

        var authentication = PrismSecurityConfiguration
                .jwtAuthenticationConverter("roles")
                .convert(jwt);

        assertTrue(authentication.getAuthorities().stream()
                .noneMatch(authority ->
                        authority.getAuthority().startsWith("ROLE_")));
    }

    @Test
    void administrator_can_access_dashboard_get() throws Exception {
        mockMvc.perform(
                        get("/api/v1/dashboard/overview")
                                .with(jwt().authorities(
                                        new SimpleGrantedAuthority(
                                                "ROLE_ADMINISTRATOR"
                                        )
                                ))
                )
                .andExpect(status().isOk());
    }

    @Test
    void other_documented_roles_are_denied_dashboard_get()
            throws Exception {
        for (String role : List.of(
                "ROLE_SECURITY_ANALYST",
                "ROLE_PROJECT_MANAGER",
                "ROLE_VIEWER"
        )) {
            mockMvc.perform(
                            get("/api/v1/dashboard/overview")
                                    .with(jwt().authorities(
                                            new SimpleGrantedAuthority(role)
                                    ))
                    )
                    .andExpect(status().isForbidden());
        }
    }

    @Test
    void all_dashboard_write_methods_are_denied_for_administrator()
            throws Exception {
        SimpleGrantedAuthority administrator =
                new SimpleGrantedAuthority("ROLE_ADMINISTRATOR");

        mockMvc.perform(
                        post("/api/v1/dashboard/overview")
                                .with(jwt().authorities(administrator))
                )
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        put("/api/v1/dashboard/overview")
                                .with(jwt().authorities(administrator))
                )
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        patch("/api/v1/dashboard/overview")
                                .with(jwt().authorities(administrator))
                )
                .andExpect(status().isForbidden());
        mockMvc.perform(
                        delete("/api/v1/dashboard/overview")
                                .with(jwt().authorities(administrator))
                )
                .andExpect(status().isForbidden());
    }

    @Test
    void unauthenticated_dashboard_requests_are_rejected()
            throws Exception {
        mockMvc.perform(get("/api/v1/dashboard/overview"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void missing_issuer_keeps_application_running_and_fails_closed() throws Exception {
        mockMvc.perform(get("/api/protected"))
                .andExpect(status().isUnauthorized());
    }

    @TestConfiguration
    static class TestJwtConfiguration {

        @Bean
        JwtDecoder jwtDecoder() {
            return token -> {
                if (!"valid-token".equals(token)) {
                    throw new BadJwtException("Invalid test token");
                }

                return Jwt.withTokenValue(token)
                        .header("alg", "none")
                        .subject("user-001")
                        .claim("roles", List.of("VIEWER"))
                        .issuedAt(Instant.now())
                        .expiresAt(Instant.now().plusSeconds(300))
                        .build();
            };
        }
    }
}
