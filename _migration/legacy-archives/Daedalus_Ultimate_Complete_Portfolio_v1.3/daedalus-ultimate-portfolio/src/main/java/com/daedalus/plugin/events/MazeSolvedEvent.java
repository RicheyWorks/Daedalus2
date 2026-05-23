package com.daedalus.plugin.events;

import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.List;
import java.util.UUID;

/** Fired after a solver completes. */
public class MazeSolvedEvent extends PluginEvent {
    private final UUID mazeId;
    private final String solverId;
    private final List<Point> path;
    private final MazeStats stats;

    public MazeSolvedEvent(Object source, UUID mazeId, String solverId,
                           List<Point> path, MazeStats stats) {
        super(source);
        this.mazeId = mazeId;
        this.solverId = solverId;
        this.path = path;
        this.stats = stats;
    }

    public UUID mazeId()     { return mazeId; }
    public String solverId() { return solverId; }
    public List<Point> path(){ return path; }
    public MazeStats stats() { return stats; }
}
