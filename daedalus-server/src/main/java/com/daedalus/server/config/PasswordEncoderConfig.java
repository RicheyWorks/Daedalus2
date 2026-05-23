// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * BCrypt password encoder bean. Lives in its own {@code @Configuration} so it stays available
 * regardless of which {@code SecurityFilterChain} is active (the dev / non-prod chain in
 * {@code SecurityConfig} or the locked-down chain in {@code ProdSecurityConfig}).
 */
@Configuration
public class PasswordEncoderConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
