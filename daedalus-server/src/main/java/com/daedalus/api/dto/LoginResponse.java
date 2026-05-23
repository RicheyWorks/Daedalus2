// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.time.Instant;

/**
 * Response body for {@code POST /api/v1/auth/login} on success.
 *
 * <p>Use the {@code token} on subsequent requests as the bearer token:
 * {@code Authorization: Bearer <token>}.
 *
 * @param token     compact-serialised signed JWT
 * @param expiresAt when the token stops being accepted (UTC instant)
 */
public record LoginResponse(String token, Instant expiresAt) {}
