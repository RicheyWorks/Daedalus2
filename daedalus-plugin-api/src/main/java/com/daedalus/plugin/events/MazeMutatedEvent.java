// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import com.daedalus.engine.MazeGrid;

import java.util.UUID;

/**
 * Fired after a living maze finishes one mutation tick (ADR-006 / ADR-008). Each tick
 * may erode (open dead-end walls), harden (close non-forest passages), and on weighted
 * grids drift hotspot costs, then swaps the new immutable snapshot into the maze cache.
 * {@code grid()} is that new snapshot; the previous grid is never modified, so listeners
 * holding it stay consistent.
 *
 * <p>Erosion only ever <em>opens</em> walls. Hardening only ever closes passages that
 * are not in a spanning forest, so every habitable cell reachable before a tick is
 * reachable after it — listeners never have to re-validate connectivity.
 */
public class MazeMutatedEvent extends PluginEvent {

    private final UUID mazeId;
    private final int tick;
    private final int wallsOpened;
    private final int wallsClosed;
    private final int deadEndsRemaining;
    private final boolean settled;
    private final MazeGrid grid;

    /**
     * v1 constructor — {@code wallsClosed} is 0. Kept so existing listeners and tests
     * compile; new call sites should use the eight-argument form.
     */
    public MazeMutatedEvent(Object source, UUID mazeId, int tick, int wallsOpened,
                            int deadEndsRemaining, boolean settled, MazeGrid grid) {
        this(source, mazeId, tick, wallsOpened, 0, deadEndsRemaining, settled, grid);
    }

    /**
     * @param tick              1-based index of this tick within its run
     * @param wallsOpened       walls carved by this tick (0 on the settling tick)
     * @param wallsClosed       walls sealed by this tick (0 when hardening is off)
     * @param deadEndsRemaining dead ends left after this tick
     * @param settled           true when this is the run's final frame — ticks exhausted,
     *                          or nothing left for erosion or hardening to change
     * @param grid              the new snapshot now served by the cache
     */
    public MazeMutatedEvent(Object source, UUID mazeId, int tick, int wallsOpened,
                            int wallsClosed, int deadEndsRemaining, boolean settled,
                            MazeGrid grid) {
        super(source);
        this.mazeId = mazeId;
        this.tick = tick;
        this.wallsOpened = wallsOpened;
        this.wallsClosed = wallsClosed;
        this.deadEndsRemaining = deadEndsRemaining;
        this.settled = settled;
        this.grid = grid;
    }

    public UUID mazeId()           { return mazeId; }
    public int tick()              { return tick; }
    public int wallsOpened()       { return wallsOpened; }
    public int wallsClosed()       { return wallsClosed; }
    public int deadEndsRemaining() { return deadEndsRemaining; }
    public boolean settled()       { return settled; }
    public MazeGrid grid()         { return grid; }
}
