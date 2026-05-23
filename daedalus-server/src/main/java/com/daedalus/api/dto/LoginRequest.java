// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Request body for {@code POST /api/v1/auth/login}.
 *
 * <p>Validation contract:
 * <ul>
 *   <li>{@code username} — required, non-blank, 1..64 characters.</li>
 *   <li>{@code password} — required, non-blank, 1..256 characters. We do not enforce a
 *       minimum length here on purpose: short passwords are rejected by the bcrypt match
 *       in the controller (returning a 401), and a 400 here would leak the policy.</li>
 * </ul>
 *
 * @param username matches the configured {@code daedalus.security.admin.username}
 * @param password plaintext password — server compares against the stored bcrypt hash
 */
public record LoginRequest(
        @NotBlank(message = "username is required")
        @Size(max = 64, message = "username must be at most 64 chars")
        String username,

        @NotBlank(message = "password is required")
        @Size(max = 256, message = "password must be at most 256 chars")
        String password
) {}
