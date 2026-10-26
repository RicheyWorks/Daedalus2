// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

import java.util.Objects;

/** The attempt was already credited to this subject. The first receipt still stands. */
public final class ActivityCreditException extends IllegalStateException {
    private static final long serialVersionUID = 1L;

    /** Same canonical body delivered again, or a different body for the same attempt and subject. */
    public enum Reason { DUPLICATE, CONFLICT }

    private final Reason reason;
    private final ActivityResultReceipt prior;

    public ActivityCreditException(Reason reason, ActivityResultReceipt prior) {
        super(sentence(reason, prior));
        this.reason = Objects.requireNonNull(reason, "reason");
        this.prior = Objects.requireNonNull(prior, "prior");
    }

    public Reason reason() {
        return reason;
    }

    /** The receipt that was credited first. Apply this one, not the delivery that was refused. */
    public ActivityResultReceipt prior() {
        return prior;
    }

    private static String sentence(Reason reason, ActivityResultReceipt prior) {
        Objects.requireNonNull(reason, "reason");
        Objects.requireNonNull(prior, "prior");
        ActivityResult result = prior.result();
        String word = reason == Reason.DUPLICATE ? "duplicate" : "conflicting";
        return word + " credit for " + result.activityId() + " " + result.attemptId() + " " + result.subjectId();
    }
}
