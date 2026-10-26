// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Something happened to the life on the islands (ADR-024). STOMP maps these to
 * {@code /topic/world/{id}/ecology}.
 *
 * <ul>
 *   <li>{@code DAY} — the ecology stepped; {@code day} is the latest day and {@code richness} the
 *       kinds now on every island (slot → count). One event per harbour tick, however many days
 *       the tick caught up.</li>
 *   <li>{@code LANDED} — ark {@code arkId} tied up at {@code slot} and {@code keys} stepped off.</li>
 *   <li>{@code BOARDED} — ark {@code arkId} cast off from {@code slot} with {@code keys} aboard as
 *       stowaways.</li>
 * </ul>
 */
public class IslandLifeEvent extends PluginEvent {

    public enum Kind {
        DAY,
        LANDED,
        BOARDED
    }

    private final String worldId;
    private final Kind kind;
    private final long day;
    private final int slot;
    private final String arkId;
    private final List<String> keys;
    private final Map<Integer, Integer> richness;

    public IslandLifeEvent(Object source, String worldId, Kind kind, long day, int slot, String arkId,
                           List<String> keys, Map<Integer, Integer> richness) {
        super(source);
        this.worldId = worldId;
        this.kind = kind;
        this.day = day;
        this.slot = slot;
        this.arkId = arkId;
        this.keys = keys == null ? List.of() : List.copyOf(keys);
        this.richness = richness == null ? Map.of() : Collections.unmodifiableMap(new TreeMap<>(richness));
    }

    public String worldId() { return worldId; }
    public Kind kind() { return kind; }
    public long day() { return day; }
    public int slot() { return slot; }
    public String arkId() { return arkId; }
    public List<String> keys() { return keys; }
    public Map<Integer, Integer> richness() { return richness; }
}
