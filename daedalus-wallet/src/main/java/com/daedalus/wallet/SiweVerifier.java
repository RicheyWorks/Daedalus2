// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

/**
 * Checks a signed Sign-In with Ethereum message (ADR-028). Every rule is one an attacker would
 * otherwise use: a message for another site (domain), another chain (chain id), an old or reused
 * nonce (replay), an expired or future-dated message, a signature by someone other than the address
 * the message names, or text that is not exactly EIP-4361.
 *
 * @param domain  the host[:port] this server answers on; the message must name it
 * @param chainId the chain sign-in is for
 * @param skew    how far {@code Issued At} may be ahead of the server clock
 */
public record SiweVerifier(String domain, long chainId, Duration skew) {

    /** What a sign-in attempt came to; {@code address} is lowercase and set only when {@code ok}. */
    public record Outcome(boolean ok, String address, String reason) {

        static Outcome refused(String reason) {
            return new Outcome(false, null, reason);
        }
    }

    public Outcome verify(String text, String signatureHex, WalletNonces nonces, Instant now) {
        Optional<SiweMessage> parsed = SiweMessage.parse(text);
        if (parsed.isEmpty()) {
            return Outcome.refused("MALFORMED");
        }
        SiweMessage m = parsed.get();
        if (!m.domain().equalsIgnoreCase(domain)) {
            return Outcome.refused("WRONG_DOMAIN");
        }
        if (m.chainId() != chainId) {
            return Outcome.refused("WRONG_CHAIN");
        }
        if (m.issuedAt().isAfter(now.plus(skew))) {
            return Outcome.refused("NOT_YET_VALID");
        }
        if (!now.isBefore(m.expirationTime())) {
            return Outcome.refused("EXPIRED");
        }
        Optional<String> signer = WalletSignature.recoverAddress(text.replace("\r\n", "\n"), signatureHex);
        if (signer.isEmpty() || !EthereumAddress.equalsNormalized(signer.get(), m.address())) {
            return Outcome.refused("BAD_SIGNATURE");
        }
        // Consume last: a bad signature must not burn someone else's outstanding nonce.
        if (!nonces.consume(m.nonce(), now)) {
            return Outcome.refused("STALE_NONCE");
        }
        return new Outcome(true, signer.get(), "OK");
    }
}
