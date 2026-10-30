// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import com.daedalus.model.Point;

import java.util.UUID;

/**
 * Fired after a fog-of-war agent takes a legal step (ADR-006 idea #7). The occupancy
 * counterpart of {@link PlayerMovedEvent}: traffic simulation treats agents and players
 * identically — a cell is crowded by whoever stands on it.
 */
public class AgentSteppedEvent extends PluginEvent {

    private final UUID mazeId;
    private final UUID agentId;
    private final Point from;
    private final Point to;

    public AgentSteppedEvent(Object source, UUID mazeId, UUID agentId, Point from, Point to) {
        super(source);
        this.mazeId = mazeId;
        this.agentId = agentId;
        this.from = from;
        this.to = to;
    }

    public UUID mazeId()  { return mazeId; }
    public UUID agentId() { return agentId; }
    public Point from()   { return from; }
    public Point to()     { return to; }
}
