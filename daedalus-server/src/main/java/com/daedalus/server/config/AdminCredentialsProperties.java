// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Single ops user used to authenticate against {@code POST /api/v1/auth/login}, bound from
 * {@code daedalus.security.admin.*}.
 *
 * <p>The password is stored as a bcrypt hash, not plaintext. To produce a hash, run:
 *
 * <pre>{@code
 *   import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
 *   System.out.println(new BCryptPasswordEncoder().encode("your-password"));
 * }</pre>
 *
 * and put the result in {@code DAEDALUS_ADMIN_PASSWORD_BCRYPT}. The plaintext is never
 * read by the server, only the hash.
 *
 * @param username       human-friendly identifier; defaults to "admin" if unset
 * @param passwordBcrypt bcrypt hash (e.g. {@code $2a$10$...}) — required in prod, optional in dev
 */
@ConfigurationProperties("daedalus.security.admin")
public record AdminCredentialsProperties(String username, String passwordBcrypt) {

    public AdminCredentialsProperties {
        if (username == null || username.isBlank()) {
            username = "admin";
        }
        // password may be null/blank in dev (login endpoint will refuse all attempts).
    }

    /** Convenience: is an admin user actually configured? */
    public boolean isConfigured() {
        return passwordBcrypt != null && !passwordBcrypt.isBlank();
    }
}
