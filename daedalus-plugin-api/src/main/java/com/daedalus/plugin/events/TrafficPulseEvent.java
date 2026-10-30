// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import com.daedalus.engine.MazeGrid;

import java.util.UUID;

/**
 * Fired after a traffic tick applies occupancy and decay to a maze (ADR-006 idea #3).
 * Occupancy (players moving, agents stepping) raises the entered cells' traversal costs;
 * each tick the costs decay back toward uniform. Weight-aware solvers consulted between
 * pulses route around the crowd — the feedback loop between play and routing.
 *
 * <p>Like {@link MazeMutatedEvent}, {@code grid()} is the freshly swapped immutable
 * snapshot; topology never changes on a traffic pulse, only costs.
 */
public class TrafficPulseEvent extends PluginEvent {

    private final UUID mazeId;
    private final int congestedCells;
    private final double peakCost;
    private final boolean settled;
    private final MazeGrid grid;

    /**
     * @param congestedCells cells currently costing more than the uniform {@code 1.0}
     * @param peakCost       the most expensive cell after this tick
     * @param settled        true when traffic tracking ends (fully decayed and quiet)
     */
    public TrafficPulseEvent(Object source, UUID mazeId, int congestedCells, double peakCost,
                             boolean settled, MazeGrid grid) {
        super(source);
        this.mazeId = mazeId;
        this.congestedCells = congestedCells;
        this.peakCost = peakCost;
        this.settled = settled;
        this.grid = grid;
    }

    public UUID mazeId()        { return mazeId; }
    public int congestedCells() { return congestedCells; }
    public double peakCost()    { return peakCost; }
    public boolean settled()    { return settled; }
    public MazeGrid grid()      { return grid; }
}
