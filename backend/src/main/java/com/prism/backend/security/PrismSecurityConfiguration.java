package com.prism.backend.security;

import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnExpression;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.convert.converter.Converter;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtDecoders;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Stream;

import static org.springframework.http.HttpStatus.UNAUTHORIZED;

@Configuration
@EnableConfigurationProperties(PrismJwtProperties.class)
public class PrismSecurityConfiguration {

    private static final Set<String> DOCUMENTED_ROLES = Set.of(
            "ADMINISTRATOR",
            "SECURITY_ANALYST",
            "PROJECT_MANAGER",
            "VIEWER"
    );

    @Bean
    SecurityFilterChain prismSecurityFilterChain(
            HttpSecurity http,
            PrismJwtProperties jwtProperties,
            ObjectProvider<JwtDecoder> jwtDecoderProvider
    ) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session
                        .sessionCreationPolicy(
                                SessionCreationPolicy.STATELESS
                        )
                )
                .authorizeHttpRequests(authorize -> authorize
                        .requestMatchers(
                                "/api/health",
                                "/actuator/health"
                        ).permitAll()
                        .requestMatchers(
                                HttpMethod.GET,
                                "/api/v1/dashboard",
                                "/api/v1/dashboard/**"
                        ).hasAuthority("ROLE_ADMINISTRATOR")
                        .requestMatchers(
                                "/api/v1/dashboard",
                                "/api/v1/dashboard/**"
                        ).denyAll()
                        .requestMatchers("/api/**")
                        .authenticated()
                        .requestMatchers("/actuator/**")
                        .authenticated()
                        .anyRequest()
                        .permitAll()
                )
                .exceptionHandling(exceptionHandling ->
                        exceptionHandling.authenticationEntryPoint(
                                new HttpStatusEntryPoint(UNAUTHORIZED)
                        )
                );

        JwtDecoder jwtDecoder = jwtDecoderProvider.getIfAvailable();

        if (jwtDecoder != null) {
            http.oauth2ResourceServer(oauth2 -> oauth2
                    .jwt(jwt -> jwt
                            .decoder(jwtDecoder)
                            .jwtAuthenticationConverter(
                                    jwtAuthenticationConverter(
                                            jwtProperties.rolesClaim()
                                    )
                            )
                    )
            );
        }

        return http.build();
    }

    @Bean
    @ConditionalOnMissingBean(JwtDecoder.class)
    @ConditionalOnExpression(
            "'${PRISM_JWT_ISSUER_URI:}' != ''"
    )
    JwtDecoder prismJwtDecoder(
            PrismJwtProperties jwtProperties
    ) {
        return JwtDecoders.fromIssuerLocation(
                jwtProperties.issuerUri()
        );
    }

    static Converter<Jwt, AbstractAuthenticationToken>
    jwtAuthenticationConverter(String rolesClaim) {
        JwtGrantedAuthoritiesConverter scopeConverter =
                new JwtGrantedAuthoritiesConverter();

        JwtAuthenticationConverter converter =
                new JwtAuthenticationConverter();

        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            LinkedHashSet<GrantedAuthority> authorities =
                    new LinkedHashSet<>();

            Collection<GrantedAuthority> scopeAuthorities =
                    scopeConverter.convert(jwt);

            if (scopeAuthorities != null) {
                authorities.addAll(scopeAuthorities);
            }

            Object roleClaim = jwt.getClaims().get(rolesClaim);

            for (String role : roleValues(roleClaim)) {
                String canonicalRole = canonicalRole(role);

                if (canonicalRole != null) {
                    authorities.add(
                            new SimpleGrantedAuthority(
                                    "ROLE_" + canonicalRole
                            )
                    );
                }
            }

            return authorities;
        });

        return converter;
    }

    private static List<String> roleValues(Object roles) {
        if (roles instanceof Collection<?> collection) {
            return collection.stream()
                    .filter(value -> value instanceof String)
                    .map(String.class::cast)
                    .map(String::trim)
                    .filter(value -> !value.isEmpty())
                    .toList();
        }

        if (roles instanceof String roleString) {
            String trimmed = roleString.trim();

            if (trimmed.isEmpty()) {
                return List.of();
            }

            if (canonicalRole(trimmed) != null) {
                return List.of(trimmed);
            }

            return Stream.of(trimmed.split("[,;|]"))
                    .map(String::trim)
                    .filter(value -> !value.isEmpty())
                    .toList();
        }

        return List.of();
    }

    private static String canonicalRole(String role) {
        if (role == null || role.isBlank()) {
            return null;
        }

        String normalized = role.trim()
                .toUpperCase(Locale.ROOT)
                .replaceAll("[\\s-]+", "_")
                .replaceAll("_+", "_");

        if (normalized.startsWith("ROLE_")) {
            normalized = normalized.substring("ROLE_".length());
        }

        return DOCUMENTED_ROLES.contains(normalized)
                ? normalized
                : null;
    }
}
