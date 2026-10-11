// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.time.Instant;

/**
 * The exact Sign-In with Ethereum message for an address to sign (ADR-028). The server writes the
 * whole message, so a client only has to pass it to {@code personal_sign} unchanged.
 */
public record WalletNonceResponse(String message, String nonce, Instant expiresAt) {
}
