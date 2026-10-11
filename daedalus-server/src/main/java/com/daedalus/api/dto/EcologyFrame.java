// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;
import java.util.Map;

/**
 * STOMP frame on {@code /topic/world/{id}/ecology} (ADR-024). {@code DAY}: the ecology reached
 * {@code day} and {@code richness} maps each island slot (as a string, JSON keys are strings) to
 * the kinds living there. {@code LANDED}/{@code BOARDED}: ark {@code arkId} put {@code keys} ashore
 * at, or took them aboard from, {@code slot}. {@code now} is the server clock when sent.
 */
public record EcologyFrame(String worldId, String kind, long day, int slot, String arkId,
                           List<String> keys, Map<String, Integer> richness, long now) {

    /** Copy on construct: the caller's collections cannot change what this record says. */
    public EcologyFrame {
        keys = keys == null ? List.of() : List.copyOf(keys);
        richness = richness == null ? Map.of() : Map.copyOf(richness);
    }
}
