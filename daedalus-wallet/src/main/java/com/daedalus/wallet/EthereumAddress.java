// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import org.web3j.crypto.Keys;

import java.util.Locale;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * Validates and normalizes Ethereum addresses (ported from ComputerPets
 * {@code com.enterprisepet.nft.EthereumAddress}).
 *
 * <p>Any 20-byte hex address with a {@code 0x} prefix. Comparison is case-insensitive, so EIP-55
 * checksummed and lowercase forms match. A bare {@code "0x"} never matches anything — ComputerPets
 * once had a {@code contains} check that let it match every ABI response.
 */
public final class EthereumAddress {

    private static final Pattern HEX = Pattern.compile("^0x[0-9a-fA-F]{40}$");

    private EthereumAddress() {
    }

    /** Lowercase {@code 0x} address, or empty when the input is not a well-formed address. */
    public static Optional<String> normalize(String raw) {
        if (raw == null) {
            return Optional.empty();
        }
        String trimmed = raw.trim();
        if (trimmed.length() == 42 && (trimmed.startsWith("0X") || trimmed.startsWith("0x"))) {
            trimmed = "0x" + trimmed.substring(2);
        }
        if (!HEX.matcher(trimmed).matches()) {
            return Optional.empty();
        }
        return Optional.of(trimmed.toLowerCase(Locale.ROOT));
    }

    public static boolean equalsNormalized(String left, String right) {
        Optional<String> a = normalize(left);
        Optional<String> b = normalize(right);
        return a.isPresent() && a.equals(b);
    }

    /** True for a well-formed address whose mixed case is a valid EIP-55 checksum (or all one case). */
    public static boolean checksumValid(String raw) {
        if (raw == null || !HEX.matcher(raw).matches()) {
            return false;
        }
        String body = raw.substring(2);
        if (body.equals(body.toLowerCase(Locale.ROOT)) || body.equals(body.toUpperCase(Locale.ROOT))) {
            return true;
        }
        return Keys.toChecksumAddress(raw).equals(raw);
    }

    /** EIP-55 mixed-case form of a valid address. */
    public static String checksummed(String raw) {
        return Keys.toChecksumAddress(normalize(raw).orElseThrow(
                () -> new IllegalArgumentException("not an Ethereum address: " + raw)));
    }
}
