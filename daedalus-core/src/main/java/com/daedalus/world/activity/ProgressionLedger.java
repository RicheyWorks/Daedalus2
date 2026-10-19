// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * In-memory reference progression authority for activity-result v1: credits each participant of a receipt
 * exactly once per (source event, instance, track). Retrying the same receipt returns the earlier awards;
 * a different receipt reusing a result id is a conflict; a new policy revision does not pay the same event again.
 * Hosts with real persistence keep the same keys and rules (or write through their durable outbox).
 */
public final class ProgressionLedger {

    /** One settled award for one participant and track. */
    public record Award(String awardKey, String instanceId, String track, String sourceKey, String receiptDigest,
                        int policyRevision, long points, long before, long after) { }

    /** Thrown when a result id is reused with a different payload. */
    public static final class ConflictException extends RuntimeException {
        public ConflictException(String message) { super(message); }
    }

    private final Map<String, String> digestBySource = new HashMap<>();
    private final Map<String, Award> awards = new LinkedHashMap<>();
    private final Map<String, Long> totals = new HashMap<>();

    /** Unique award key binding source event, life instance and track (policy and adapter revision excluded). */
    public static String awardKey(String sourceKey, String instanceId, String track) {
        return sourceKey + "|" + instanceId + "|" + track;
    }

    /** Credits every participant once and returns their awards (the earlier ones on a retry). */
    public synchronized List<Award> credit(ActivityResultReceipt receipt, AwardPolicy policy) {
        Objects.requireNonNull(receipt, "receipt");
        Objects.requireNonNull(policy, "policy");
        String source = receipt.sourceKey();
        String digest = receipt.digest();
        String known = digestBySource.get(resultKey(receipt));
        if (known != null && !known.equals(digest))
            throw new ConflictException("result " + receipt.resultId() + " already accepted with a different payload");
        long points = policy.points(receipt);
        List<Award> out = new ArrayList<>();
        List<Award> fresh = new ArrayList<>();
        for (ActivityParticipant p : receipt.participants()) {
            String key = awardKey(source, p.instanceId(), policy.track());
            Award prior = awards.get(key);
            if (prior != null) { out.add(prior); continue; }
            String tk = p.instanceId() + "|" + policy.track();
            long before = totals.getOrDefault(tk, 0L) + fresh.stream()
                    .filter(a -> a.instanceId().equals(p.instanceId())).mapToLong(Award::points).sum();
            Award a = new Award(key, p.instanceId(), policy.track(), source, digest, policy.revision(), points,
                    before, Math.addExact(before, points));
            fresh.add(a);
            out.add(a);
        }
        // apply atomically: all fresh awards or none
        digestBySource.put(resultKey(receipt), digest);
        for (Award a : fresh) {
            awards.put(a.awardKey(), a);
            totals.put(a.instanceId() + "|" + a.track(), a.after());
        }
        return List.copyOf(out);
    }

    /** Learned points on a track for one instance. */
    public synchronized long total(String instanceId, String track) {
        return totals.getOrDefault(instanceId + "|" + track, 0L);
    }

    /** Contribution history for one instance, oldest first. */
    public synchronized List<Award> history(String instanceId) {
        return awards.values().stream().filter(a -> a.instanceId().equals(instanceId)).toList();
    }

    private static String resultKey(ActivityResultReceipt r) { return r.activityId() + "|" + r.resultId(); }
}
