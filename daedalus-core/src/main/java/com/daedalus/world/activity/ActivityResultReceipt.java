// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.SortedMap;
import java.util.TreeMap;

/**
 * Immutable activity-result v1 receipt. It names the schema, result and session, the definition and revision, the
 * authority that verified the game result, the terminal outcome, the accepted participants and their roles,
 * bounded contribution measures, source event references and the authoritative clock boundary. A client never
 * supplies an XP total: measures are game facts and the progression authority turns them into awards.
 *
 * <p>{@link #toJson()} is canonical (fixed key order, sorted measures) so the same receipt always has the same
 * {@link #digest()}; a resubmitted result with the same id but a different digest is a conflict.
 */
public record ActivityResultReceipt(String resultId, String sessionId, String activityId, int definitionRevision,
                                    ActivityMode mode, String issuer, String verificationRef, ActivityOutcome outcome,
                                    List<ActivityParticipant> participants, SortedMap<String, Long> measures,
                                    List<String> sourceEventRefs, long clockBoundaryMs) {

    public static final String SCHEMA = "activity-result-v1";

    public ActivityResultReceipt {
        resultId = ActivityParticipant.key(resultId, "resultId");
        sessionId = ActivityParticipant.key(sessionId, "sessionId");
        activityId = ActivityParticipant.key(activityId, "activityId");
        issuer = ActivityParticipant.key(issuer, "issuer");
        verificationRef = ActivityParticipant.key(verificationRef, "verificationRef");
        Objects.requireNonNull(mode, "mode");
        Objects.requireNonNull(outcome, "outcome");
        if (definitionRevision < 1) throw new IllegalArgumentException("definitionRevision must be >= 1");
        if (clockBoundaryMs < 0) throw new IllegalArgumentException("clockBoundaryMs must be >= 0");
        participants = List.copyOf(Objects.requireNonNull(participants, "participants"));
        if (participants.isEmpty()) throw new IllegalArgumentException("at least one participant required");
        HashSet<String> seen = new HashSet<>();
        for (ActivityParticipant p : participants)
            if (!seen.add(p.instanceId())) throw new IllegalArgumentException("duplicate participant " + p.instanceId());
        measures = Collections.unmodifiableSortedMap(new TreeMap<>(Objects.requireNonNull(measures, "measures")));
        sourceEventRefs = List.copyOf(Objects.requireNonNull(sourceEventRefs, "sourceEventRefs"));
        sourceEventRefs.forEach(r -> ActivityParticipant.key(r, "sourceEventRef"));
    }

    /** Builds a receipt after checking participants and measures against the definition. */
    public static ActivityResultReceipt issue(ActivityDefinition def, String resultId, String sessionId, String issuer,
                                              String verificationRef, ActivityOutcome outcome,
                                              List<ActivityParticipant> participants, Map<String, Long> measures,
                                              List<String> sourceEventRefs, long clockBoundaryMs) {
        Objects.requireNonNull(def, "definition");
        if (participants.size() > def.maxParticipants())
            throw new IllegalArgumentException("too many participants for " + def.activityId());
        participants.forEach(def::checkParticipant);
        measures.forEach(def::checkMeasure);
        return new ActivityResultReceipt(resultId, sessionId, def.activityId(), def.revision(), def.mode(), issuer,
                verificationRef, outcome, participants, new TreeMap<>(measures), sourceEventRefs, clockBoundaryMs);
    }

    /** Canonical single-line JSON (the activity-result v1 wire form). */
    public String toJson() {
        StringBuilder b = new StringBuilder(256);
        b.append("{\"schema\":\"").append(SCHEMA).append('"')
         .append(",\"resultId\":\"").append(resultId).append('"')
         .append(",\"sessionId\":\"").append(sessionId).append('"')
         .append(",\"activityId\":\"").append(activityId).append('"')
         .append(",\"definitionRevision\":").append(definitionRevision)
         .append(",\"mode\":\"").append(mode).append('"')
         .append(",\"issuer\":\"").append(issuer).append('"')
         .append(",\"verificationRef\":\"").append(verificationRef).append('"')
         .append(",\"outcome\":\"").append(outcome).append('"')
         .append(",\"participants\":[");
        for (int i = 0; i < participants.size(); i++) {
            ActivityParticipant p = participants.get(i);
            if (i > 0) b.append(',');
            b.append("{\"instanceId\":\"").append(p.instanceId()).append("\",\"kind\":\"").append(p.kind())
             .append("\",\"profile\":\"").append(p.profile()).append("\",\"role\":\"").append(p.role()).append("\"}");
        }
        b.append("],\"measures\":{");
        List<String> parts = new ArrayList<>();
        measures.forEach((k, v) -> parts.add("\"" + k + "\":" + v));
        b.append(String.join(",", parts)).append("},\"sourceEventRefs\":[");
        List<String> refs = new ArrayList<>();
        sourceEventRefs.forEach(r -> refs.add("\"" + r + "\""));
        b.append(String.join(",", refs)).append("],\"clockBoundaryMs\":").append(clockBoundaryMs).append('}');
        return b.toString();
    }

    /** SHA-256 of {@link #toJson()} as lowercase hex. */
    public String digest() {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(md.digest(toJson().getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Canonical source key that an award is bound to: activity, session and result, independent of revision. */
    public String sourceKey() { return activityId + "|" + sessionId + "|" + resultId; }
}
