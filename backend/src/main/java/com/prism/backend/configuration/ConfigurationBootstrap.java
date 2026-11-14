package com.prism.backend.configuration;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Configuration bootstrap enabling typed property binding.
 * <p>
 * This class enables configuration properties binding for all
 * PRISM configuration records and validates startup requirements.
 */
@Configuration
@EnableConfigurationProperties({
        ApiConfigurationProperties.class,
        FlaskServiceConfigurationProperties.class
})
public class ConfigurationBootstrap {
}
