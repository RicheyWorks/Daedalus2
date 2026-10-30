// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

/**
 * An ark cast off or tied up (ADR-020). STOMP maps these to {@code /topic/world/{id}/arks}, beside
 * the block events — a world event frame stays cube-shaped. Times are server epoch milliseconds.
 * Plugins may listen: an arrival is the moment a cargo of colonists reaches an island.
 */
public class ArkVoyageEvent extends PluginEvent {

    public enum Kind {
        DEPARTED,
        ARRIVED
    }

    private final String worldId;
    private final Kind kind;
    private final String arkId;
    private final int fromSlot;
    private final int toSlot;
    private final long departAt;
    private final long arriveAt;

    public ArkVoyageEvent(Object source, String worldId, Kind kind, String arkId, int fromSlot,
                          int toSlot, long departAt, long arriveAt) {
        super(source);
        this.worldId = worldId;
        this.kind = kind;
        this.arkId = arkId;
        this.fromSlot = fromSlot;
        this.toSlot = toSlot;
        this.departAt = departAt;
        this.arriveAt = arriveAt;
    }

    public String worldId() { return worldId; }
    public Kind kind() { return kind; }
    public String arkId() { return arkId; }
    public int fromSlot() { return fromSlot; }
    public int toSlot() { return toSlot; }
    public long departAt() { return departAt; }
    public long arriveAt() { return arriveAt; }
}
