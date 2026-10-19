// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;

/**
 * The credit for one envelope. The id is the SHA-256 of {@link ActivityResult#serialize()},
 * so a replay names the same receipt. {@link #issue} refuses a second credit.
 */
public record ActivityResultReceipt(String receiptId, ActivityResult result) {

    public ActivityResultReceipt {
        Objects.requireNonNull(result, "result");
        Objects.requireNonNull(receiptId, "receiptId");
        if (!receiptId.equals(idOf(result))) {
            throw new IllegalArgumentException("activity-result: receipt id does not match the envelope");
        }
    }

    /** Lowercase hex SHA-256 of the canonical envelope. Stable across ledgers and restarts. */
    public static String idOf(ActivityResult result) {
        Objects.requireNonNull(result, "result");
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(result.serialize().getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is required by every JVM", ex);
        }
    }

    /**
     * Credits {@code result} through {@code credit}. A duplicate or a conflicting retry is refused
     * and the subject is not credited again.
     */
    public static ActivityResultReceipt issue(ActivityCredit credit, ActivityResult result) {
        Objects.requireNonNull(credit, "credit");
        Objects.requireNonNull(result, "result");
        return credit.credit(result);
    }
}
