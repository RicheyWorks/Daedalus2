// SPDX-License-Identifier: MIT

package com.daedalus.world.activity;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Pattern;

/**
 * A finished activity and the lesson it credits to one creature or plant.
 * Parsing, the constructor, and {@link #serialize()} are the v1 contract in
 * {@code docs/contracts/activity-result-v1}.
 */
public record ActivityResult(
        String version,
        String activityId,
        String attemptId,
        String subjectId,
        SubjectKind subjectKind,
        Outcome outcome,
        String learned,
        Map<String, String> detail) {

    public static final String VERSION = "activity-result/v1";
    /** Envelopes are small on purpose. A larger body is a different contract. */
    public static final int MAX_JSON = 4096;
    public static final int MAX_DETAIL = 8;

    private static final Pattern ACTIVITY_ID = Pattern.compile("^[a-z0-9]([a-z0-9.-]{0,62}[a-z0-9])?$");
    private static final Pattern TOKEN = Pattern.compile("^[A-Za-z0-9]([A-Za-z0-9._:-]{0,62}[A-Za-z0-9])?$");
    private static final Pattern DETAIL_KEY = Pattern.compile("^[a-z]([a-z0-9-]{0,30}[a-z0-9])?$");
    private static final Set<String> FIELDS = Set.of(
            "version", "activityId", "attemptId", "subjectId", "subjectKind", "outcome", "learned", "detail");
    private static final List<String> REQUIRED = List.of(
            "version", "activityId", "attemptId", "subjectId", "subjectKind", "outcome", "learned");

    public enum SubjectKind { CREATURE, PLANT }

    public enum Outcome { LEARNED, COMPLETED, MISSED, FAILED }

    public ActivityResult {
        version = required(version, "version");
        if (!VERSION.equals(version)) {
            throw new IllegalArgumentException("activity-result: version must be " + VERSION);
        }
        activityId = token(activityId, "activityId", ACTIVITY_ID);
        attemptId = token(attemptId, "attemptId", TOKEN);
        subjectId = token(subjectId, "subjectId", TOKEN);
        if (subjectKind == null) {
            throw new IllegalArgumentException("activity-result: subjectKind is required");
        }
        if (outcome == null) {
            throw new IllegalArgumentException("activity-result: outcome is required");
        }
        learned = token(learned, "learned", TOKEN);
        detail = copyDetail(detail);
    }

    /** Parses and validates one v1 envelope. */
    public static ActivityResult parse(String json) {
        if (json == null) {
            throw new IllegalArgumentException("activity-result: json is required");
        }
        if (json.length() > MAX_JSON) {
            throw new IllegalArgumentException("activity-result: json exceeds " + MAX_JSON + " characters");
        }
        Object value;
        try {
            value = ActivityJson.parse(json);
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("activity-result: " + ex.getMessage(), ex);
        }
        if (!(value instanceof Map<?, ?> raw)) {
            throw new IllegalArgumentException("activity-result: envelope must be an object");
        }
        Map<String, Object> map = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : raw.entrySet()) {
            map.put((String) entry.getKey(), entry.getValue());
        }
        for (String key : map.keySet()) {
            if (!FIELDS.contains(key)) {
                throw new IllegalArgumentException("activity-result: unknown field " + key);
            }
        }
        for (String key : REQUIRED) {
            if (!map.containsKey(key)) {
                throw new IllegalArgumentException("activity-result: missing " + key);
            }
        }
        return new ActivityResult(
                text(map.get("version"), "version"),
                text(map.get("activityId"), "activityId"),
                text(map.get("attemptId"), "attemptId"),
                text(map.get("subjectId"), "subjectId"),
                kind(map.get("subjectKind")),
                outcome(map.get("outcome")),
                text(map.get("learned"), "learned"),
                detailMap(map.get("detail"), map.containsKey("detail")));
    }

    /** Canonical v1 bytes, without a trailing newline. The receipt id hashes this. */
    public String serialize() {
        StringBuilder b = new StringBuilder(256);
        b.append('{');
        field(b, "version", version, true);
        field(b, "activityId", activityId, false);
        field(b, "attemptId", attemptId, false);
        field(b, "subjectId", subjectId, false);
        field(b, "subjectKind", subjectKind.name(), false);
        field(b, "outcome", outcome.name(), false);
        field(b, "learned", learned, false);
        if (!detail.isEmpty()) {
            b.append(",\"detail\":{");
            boolean first = true;
            for (Map.Entry<String, String> entry : detail.entrySet()) {
                if (!first) {
                    b.append(',');
                }
                first = false;
                b.append(ActivityJson.quote(entry.getKey())).append(':').append(ActivityJson.quote(entry.getValue()));
            }
            b.append('}');
        }
        b.append('}');
        return b.toString();
    }

    private static void field(StringBuilder b, String key, String value, boolean first) {
        if (!first) {
            b.append(',');
        }
        b.append(ActivityJson.quote(key)).append(':').append(ActivityJson.quote(value));
    }

    private static Map<String, String> detailMap(Object raw, boolean present) {
        if (!present) {
            return Map.of();
        }
        if (!(raw instanceof Map<?, ?> map)) {
            throw new IllegalArgumentException("activity-result: detail must be an object");
        }
        if (map.isEmpty()) {
            throw new IllegalArgumentException("activity-result: detail must not be empty");
        }
        Map<String, String> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            if (!(entry.getValue() instanceof String value)) {
                throw new IllegalArgumentException("activity-result: detail values must be strings");
            }
            out.put((String) entry.getKey(), value);
        }
        return out;
    }

    private static Map<String, String> copyDetail(Map<String, String> detail) {
        if (detail == null || detail.isEmpty()) {
            return Map.of();
        }
        if (detail.size() > MAX_DETAIL) {
            throw new IllegalArgumentException("activity-result: detail has more than " + MAX_DETAIL + " entries");
        }
        TreeMap<String, String> copy = new TreeMap<>();
        for (Map.Entry<String, String> entry : detail.entrySet()) {
            if (entry.getKey() == null || entry.getValue() == null) {
                throw new IllegalArgumentException("activity-result: detail entries are required");
            }
            String key = token(entry.getKey(), "detail key", DETAIL_KEY);
            copy.put(key, detailValue(entry.getValue(), key));
        }
        return Collections.unmodifiableMap(copy);
    }

    private static SubjectKind kind(Object raw) {
        if (!(raw instanceof String value) || (!"CREATURE".equals(value) && !"PLANT".equals(value))) {
            throw new IllegalArgumentException("activity-result: subjectKind must be CREATURE or PLANT");
        }
        return SubjectKind.valueOf(value);
    }

    private static Outcome outcome(Object raw) {
        if (!(raw instanceof String value)) {
            throw new IllegalArgumentException("activity-result: outcome must be a string");
        }
        for (Outcome outcome : Outcome.values()) {
            if (outcome.name().equals(value)) {
                return outcome;
            }
        }
        throw new IllegalArgumentException("activity-result: outcome must be LEARNED, COMPLETED, MISSED, or FAILED");
    }

    private static String text(Object raw, String field) {
        if (!(raw instanceof String value)) {
            throw new IllegalArgumentException("activity-result: " + field + " must be a string");
        }
        return value;
    }

    private static String required(String value, String field) {
        if (value == null) {
            throw new IllegalArgumentException("activity-result: " + field + " is required");
        }
        return value;
    }

    private static String token(String value, String field, Pattern pattern) {
        if (value == null) {
            throw new IllegalArgumentException("activity-result: " + field + " is required");
        }
        if (!pattern.matcher(value).matches()) {
            throw new IllegalArgumentException("activity-result: bad " + field);
        }
        return value;
    }

    private static String detailValue(String value, String key) {
        if (value.isEmpty() || value.length() > 96) {
            throw new IllegalArgumentException("activity-result: detail." + key + " must be 1..96 characters");
        }
        for (int n = 0; n < value.length(); n++) {
            char c = value.charAt(n);
            if (c < 0x20 || c > 0x7E) {
                throw new IllegalArgumentException("activity-result: detail." + key + " must be printable ASCII");
            }
        }
        return value;
    }
}
