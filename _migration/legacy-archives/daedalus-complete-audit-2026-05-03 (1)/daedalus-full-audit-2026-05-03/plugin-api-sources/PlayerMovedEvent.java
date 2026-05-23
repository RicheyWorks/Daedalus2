package com.daedalus.plugin.events;

import com.daedalus.model.Point;

import java.util.UUID;

/** Fired on every player move within a session. */
public class PlayerMovedEvent extends PluginEvent {
    private final UUID sessionId;
    private final Point from;
    private final Point to;

    public PlayerMovedEvent(Object source, UUID sessionId, Point from, Point to) {
        super(source);
        this.sessionId = sessionId;
        this.from = from;
        this.to = to;
    }

    public UUID sessionId() { return sessionId; }
    public Point from()     { return from; }
    public Point to()       { return to; }
}
