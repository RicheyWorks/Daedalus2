package com.daedalus.plugin.events;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeMetadata;
import com.daedalus.model.MazeStats;

/** Fired after a maze is fully generated. */
public class MazeGeneratedEvent extends PluginEvent {
    private final MazeMetadata metadata;
    private final MazeGrid grid;
    private final MazeStats stats;

    public MazeGeneratedEvent(Object source, MazeMetadata metadata, MazeGrid grid, MazeStats stats) {
        super(source);
        this.metadata = metadata;
        this.grid = grid;
        this.stats = stats;
    }

    public MazeMetadata metadata() { return metadata; }
    public MazeGrid grid()         { return grid; }
    public MazeStats stats()       { return stats; }
}
