// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.Point;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.World;
import com.daedalus.world.stamp.StampOps;
import com.daedalus.world.stamp.StampRequest;
import com.daedalus.world.stamp.StampResult;

/** Deterministic starter terrain using the existing maze generator and atomic voxel stamper. */
public final class LabyrinthTerrain {
    public static final int CELLS = 31;
    public static final int SCALE = 3;
    public static final int SIDE = (2 * CELLS + 1) * SCALE;
    public static final int WALL_HEIGHT = 3;
    public static final BlockCoordinate ORIGIN = new BlockCoordinate(-SIDE / 2, 0, -SIDE / 2);

    private LabyrinthTerrain() { }

    public static MazeGrid maze(long seed) {
        MazeGrid maze = new RecursiveBacktrackerGenerator().generate(CELLS, CELLS, seed);
        maze.setStart(new Point(0, 0));
        maze.setGoal(new Point(CELLS - 1, CELLS - 1));
        maze.cell(0, 0).open(Direction.NORTH);
        maze.cell(CELLS - 1, CELLS - 1).open(Direction.SOUTH);
        return maze;
    }

    /** Feet anchor in Java +Y-up metres; add pawn half-height when positioning a capsule. */
    public static BlockCoordinate spawn() {
        return new BlockCoordinate(ORIGIN.x() + SCALE + SCALE / 2, 1, ORIGIN.z() + SCALE / 2);
    }

    public static BlockCoordinate exit() {
        return new BlockCoordinate(ORIGIN.x() + (2 * CELLS - 1) * SCALE + SCALE / 2,
                1, ORIGIN.z() + (2 * CELLS) * SCALE + SCALE / 2);
    }

    /** Host calls under its mutation lock, once on an empty world; never overwrite an existing volume. */
    public static StampResult build(World world, long seed) {
        if (world.chunkCount() != 0 || !world.parcels().isEmpty()) return StampResult.overlap(world.revision());
        return StampOps.apply(world, new StampRequest(world.id(), ORIGIN, maze(seed), 0, WALL_HEIGHT, SCALE));
    }
}
