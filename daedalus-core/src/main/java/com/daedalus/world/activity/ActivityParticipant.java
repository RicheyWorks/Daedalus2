// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.util.Objects;
import java.util.regex.Pattern;

/**
 * One accepted participant in an activity session: an individual life ({@code lifeInstanceId}) or a colony
 * (hive, school, fungal patch, culture) identified by {@code colonyInstanceId}. Profile and role are canonical keys
 * (e.g. profile {@code animal}, role {@code scouting}); the species key itself is never changed by an activity.
 */
public record ActivityParticipant(String instanceId, Kind kind, String profile, String role) {

    /** Management unit of the participant. */
    public enum Kind { LIFE, COLONY }

    static final Pattern KEY = Pattern.compile("[a-z0-9][a-z0-9_.:-]{0,95}");

    public ActivityParticipant {
        instanceId = key(instanceId, "instanceId");
        Objects.requireNonNull(kind, "kind");
        profile = key(profile, "profile");
        role = key(role, "role");
    }

    static String key(String value, String name) {
        if (value == null || !KEY.matcher(value).matches())
            throw new IllegalArgumentException(name + " must match " + KEY.pattern() + ": " + value);
        return value;
    }
}
