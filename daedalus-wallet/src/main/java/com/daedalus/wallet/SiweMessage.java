// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.Objects;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * A Sign-In with Ethereum message (EIP-4361), the text a wallet shows its holder before they sign.
 * Only the fields Daedalus uses: domain, address, statement, URI, version 1, chain id, nonce, issued
 * at and expiration. {@link #toText()} and {@link #parse(String)} are exact inverses.
 *
 * <pre>
 * realm.example wants you to sign in with your Ethereum account:
 * 0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B
 *
 * Sign in to the Daedalus Realm.
 *
 * URI: https://realm.example
 * Version: 1
 * Chain ID: 11155111
 * Nonce: 3f9c1d0b7a6e4c2d
 * Issued At: 2026-10-11T15:00:00Z
 * Expiration Time: 2026-10-11T15:10:00Z
 * </pre>
 */
public record SiweMessage(String domain, String address, String statement, String uri, long chainId,
                          String nonce, Instant issuedAt, Instant expirationTime) {

    private static final Pattern DOMAIN = Pattern.compile("^[A-Za-z0-9.-]+(:[0-9]{1,5})?$");
    private static final Pattern NONCE = Pattern.compile("^[A-Za-z0-9]{8,64}$");
    private static final Pattern TEXT = Pattern.compile(
            "^(?<domain>[^\\n ]+) wants you to sign in with your Ethereum account:\\n"
                    + "(?<address>0x[0-9a-fA-F]{40})\\n\\n"
                    + "(?<statement>[^\\n]*)\\n\\n"
                    + "URI: (?<uri>[^\\n]+)\\n"
                    + "Version: 1\\n"
                    + "Chain ID: (?<chain>[0-9]{1,18})\\n"
                    + "Nonce: (?<nonce>[^\\n]+)\\n"
                    + "Issued At: (?<iat>[^\\n]+)\\n"
                    + "Expiration Time: (?<exp>[^\\n]+)$");

    public SiweMessage {
        Objects.requireNonNull(issuedAt, "issuedAt");
        Objects.requireNonNull(expirationTime, "expirationTime");
        if (domain == null || !DOMAIN.matcher(domain).matches()) {
            throw new IllegalArgumentException("domain must be a host[:port]");
        }
        if (!EthereumAddress.checksumValid(address)) {
            throw new IllegalArgumentException("address must be a 0x address with a valid EIP-55 checksum");
        }
        statement = statement == null ? "" : statement;
        if (statement.contains("\n")) {
            throw new IllegalArgumentException("statement must be one line");
        }
        if (uri == null || uri.isBlank() || uri.contains("\n")) {
            throw new IllegalArgumentException("uri is required");
        }
        if (chainId < 1) {
            throw new IllegalArgumentException("chainId must be positive");
        }
        if (nonce == null || !NONCE.matcher(nonce).matches()) {
            throw new IllegalArgumentException("nonce must be 8-64 letters or digits (EIP-4361)");
        }
        if (!expirationTime.isAfter(issuedAt)) {
            throw new IllegalArgumentException("expirationTime must be after issuedAt");
        }
    }

    public String toText() {
        return domain + " wants you to sign in with your Ethereum account:\n"
                + address + "\n\n"
                + statement + "\n\n"
                + "URI: " + uri + "\n"
                + "Version: 1\n"
                + "Chain ID: " + chainId + "\n"
                + "Nonce: " + nonce + "\n"
                + "Issued At: " + issuedAt + "\n"
                + "Expiration Time: " + expirationTime;
    }

    /** The message a wallet signed, or empty if the text is not exactly this shape. */
    public static Optional<SiweMessage> parse(String text) {
        if (text == null) {
            return Optional.empty();
        }
        Matcher m = TEXT.matcher(text.replace("\r\n", "\n"));
        if (!m.matches()) {
            return Optional.empty();
        }
        try {
            return Optional.of(new SiweMessage(m.group("domain"), m.group("address"), m.group("statement"),
                    m.group("uri"), Long.parseLong(m.group("chain")), m.group("nonce"),
                    Instant.parse(m.group("iat")), Instant.parse(m.group("exp"))));
        } catch (IllegalArgumentException | DateTimeParseException e) {
            return Optional.empty();
        }
    }
}
