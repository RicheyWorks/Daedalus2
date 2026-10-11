// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** A signed sign-in message: the message text the server issued and the wallet's signature of it. */
public record WalletSignInRequest(
        @NotBlank(message = "message is required") @Size(max = 2048, message = "message is too long") String message,
        @NotBlank(message = "signature is required") @Size(max = 140, message = "signature is too long") String signature) {
}
