// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import com.daedalus.model.Point;

import java.util.UUID;

/** Fired on every player move within a session. */
public class PlayerMovedEvent extends PluginEvent {
    private final UUID sessionId;
    private final String player;
    private final Point from;
    private final Point to;

    /** Single-player form — {@link #player()} is {@code null}. Kept for source compatibility. */
    public PlayerMovedEvent(Object source, UUID sessionId, Point from, Point to) {
        this(source, sessionId, null, from, to);
    }

    /**
     * @param player display name of the player who moved, or {@code null} when the publisher
     *               predates multiplayer sessions. Additive on 2026-07-28 for the multiplayer
     *               feature flag; existing listeners that ignore it keep working unchanged.
     */
    public PlayerMovedEvent(Object source, UUID sessionId, String player, Point from, Point to) {
        super(source);
        this.sessionId = sessionId;
        this.player = player;
        this.from = from;
        this.to = to;
    }

    public UUID sessionId() { return sessionId; }
    /** Who moved, or {@code null} from pre-multiplayer publishers. */
    public String player()  { return player; }
    public Point from()     { return from; }
    public Point to()       { return to; }
}
