// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * In-memory exactly-once ledger. One credit per {@code (activityId, attemptId, subjectId)}.
 * The host persists receipts and {@link #remember}s them after a restart; this object is not a database.
 */
public final class ActivityCreditLedger implements ActivityCredit {
    private final Object lock = new Object();
    private final Map<String, ActivityResultReceipt> byKey = new LinkedHashMap<>();

    @Override
    public ActivityResultReceipt credit(ActivityResult result) {
        Objects.requireNonNull(result, "result");
        synchronized (lock) {
            String key = key(result);
            ActivityResultReceipt prior = byKey.get(key);
            if (prior != null) {
                throw refuse(prior, result);
            }
            ActivityResultReceipt receipt = new ActivityResultReceipt(ActivityResultReceipt.idOf(result), result);
            byKey.put(key, receipt);
            return receipt;
        }
    }

    @Override
    public void remember(ActivityResultReceipt receipt) {
        Objects.requireNonNull(receipt, "receipt");
        synchronized (lock) {
            String key = key(receipt.result());
            ActivityResultReceipt prior = byKey.get(key);
            if (prior == null) {
                byKey.put(key, receipt);
                return;
            }
            if (prior.equals(receipt)) {
                return;
            }
            throw refuse(prior, receipt.result());
        }
    }

    /** How many distinct attempts are credited. */
    public int size() {
        synchronized (lock) {
            return byKey.size();
        }
    }

    /** The receipt for this triple, or empty when it has not been credited. */
    public Optional<ActivityResultReceipt> find(String activityId, String attemptId, String subjectId) {
        ActivityResult probe = new ActivityResult(
                ActivityResult.VERSION, activityId, attemptId, subjectId,
                ActivityResult.SubjectKind.CREATURE, ActivityResult.Outcome.COMPLETED, "lookup", Map.of());
        synchronized (lock) {
            return Optional.ofNullable(byKey.get(key(probe)));
        }
    }

    private static ActivityCreditException refuse(ActivityResultReceipt prior, ActivityResult incoming) {
        ActivityCreditException.Reason reason = prior.result().equals(incoming)
                ? ActivityCreditException.Reason.DUPLICATE
                : ActivityCreditException.Reason.CONFLICT;
        return new ActivityCreditException(reason, prior);
    }

    private static String key(ActivityResult result) {
        return result.activityId() + "\n" + result.attemptId() + "\n" + result.subjectId();
    }
}
