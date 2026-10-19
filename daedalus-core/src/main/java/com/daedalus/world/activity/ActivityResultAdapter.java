// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.util.List;

/**
 * Wraps one existing game's own result type {@code R} into an activity-result v1 receipt. Implement one adapter
 * per game; the game keeps its rules and the adapter only maps facts to bounded measures.
 */
public interface ActivityResultAdapter<R> {

    /** The definition this adapter issues receipts for. */
    ActivityDefinition definition();

    /** Session facts supplied by the host that ran the game (ids, authority, clock). */
    record Session(String sessionId, String resultId, String issuer, String verificationRef,
                   List<ActivityParticipant> participants, List<String> sourceEventRefs, long clockBoundaryMs) { }

    /** Turns the game's result into a receipt; throws if the result does not fit the definition. */
    ActivityResultReceipt toReceipt(Session session, R result);
}
