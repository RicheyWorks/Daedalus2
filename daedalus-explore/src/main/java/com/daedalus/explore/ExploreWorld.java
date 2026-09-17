// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.Parcel;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;
import com.daedalus.world.WorldStore;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * One extruded dungeon: mesh, body, fog, markers, living replace, traffic.
 */
public final class ExploreWorld {

    public static final int DEFAULT_ROWS = 21;
    public static final int DEFAULT_COLS = 31;
    public static final long DEFAULT_SEED = 7L;
    public static final double WALK_SPEED = 4.2;
    /** Inspired toponym on the sample landmark — same letters as the well. */
    public static final String SAMPLE_PLACE = "Willow Walk";

    private final String generatorId;
    private final long seed;
    private MazeGrid grid;
    private ExploreMesh mesh;
    private final ExploreBody body;
    private final ExploreFog fog = new ExploreFog();
    private List<ExploreMarker> markers;
    private final ExploreSession session = new ExploreSession();
    private WorldMesh blocks;
    private boolean showBlocks;
    private long blocksRevision = Long.MIN_VALUE;

    public ExploreWorld(String generatorId, long seed, MazeGrid grid) {
        this.generatorId = generatorId == null ? "dungeon" : generatorId;
        this.seed = seed;
        this.grid = grid;
        this.mesh = ExploreMesh.of(grid);
        this.body = ExploreBody.atCell(grid.start());
        faceFirstOpening(grid, this.body);
        this.markers = ExploreMarkers.plan(grid);
        fog.stand(grid.start());
    }

    public static ExploreWorld dungeon() {
        return dungeon(DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_SEED);
    }

    public static ExploreWorld dungeon(int rows, int cols, long seed) {
        MazeGrid grid = new DungeonGenerator().generate(rows, cols, seed, new MazeStats());
        return new ExploreWorld("dungeon", seed, grid);
    }

    public String generatorId() {
        return generatorId;
    }

    public long seed() {
        return seed;
    }

    public MazeGrid grid() {
        return grid;
    }

    public ExploreMesh mesh() {
        return mesh;
    }

    /**
     * Second mesh. Does not replace {@link #mesh()} — corridor KEEP stays loaded.
     */
    public WorldMesh blocks() {
        return blocks;
    }

    public void attachBlocks(World world) {
        this.blocks = world == null ? null : WorldMesh.of(world);
        this.blocksRevision = world == null ? Long.MIN_VALUE : world.revision().value();
        if (this.blocks == null) {
            this.showBlocks = false;
        }
    }

    /**
     * Rebuild the voxel mesh when the live world revision moved.
     * Corridor {@link #mesh()} stays. Collision already reads {@link World#contains}.
     */
    public void syncBlocks() {
        if (blocks == null || blocks.world() == null) {
            return;
        }
        long revision = blocks.world().revision().value();
        if (revision == blocksRevision) {
            return;
        }
        this.blocks = WorldMesh.of(blocks.world());
        this.blocksRevision = revision;
    }

    public void showBlocks(boolean show) {
        this.showBlocks = show && blocks != null;
    }

    public boolean showingBlocks() {
        return showBlocks;
    }

    /**
     * In-memory landmark slab beside the corridor. Not the server file store.
     * Maze {@link #mesh()} stays loaded.
     */
    public void attachSampleBlocks() {
        World slab = World.zero();
        slab.applyStamp(new ParcelBounds(8, 0, 8, 9, 1, 9), Parcel.SYSTEM_OWNER,
                List.of(new BlockCoordinate(8, 0, 8), new BlockCoordinate(9, 0, 8),
                        new BlockCoordinate(8, 0, 9), new BlockCoordinate(8, 1, 8)),
                List.of(BlockType.STONE, BlockType.DIRT, BlockType.WOOD, BlockType.GLASS));
        slab.nameParcel(slab.parcels().get(0).id(), SAMPLE_PLACE);
        attachBlocks(slab);
        showBlocks(true);
    }

    /**
     * Walk the same DAEW file the well persists. Missing or unreadable
     * files keep the sample landmark. Corridor {@link #mesh()} stays.
     */
    public void attachStoredOrSample(Path file) {
        if (file != null) {
            try {
                if (Files.isRegularFile(file)) {
                    attachBlocks(WorldStore.load(file));
                    showBlocks(true);
                    return;
                }
            } catch (IOException e) {
                // sample landmark still walks
            }
        }
        attachSampleBlocks();
    }

    public ExploreBody body() {
        return body;
    }

    public ExploreFog fog() {
        return fog;
    }

    public List<ExploreMarker> markers() {
        return markers;
    }

    public ExploreSession session() {
        return session;
    }

    public ExploreWalk.Outcome apply(ExploreInput.Intent intent, double dt) {
        syncBlocks();
        ExploreInput.applyLook(body, intent);
        double[] move = ExploreInput.moveVector(body, intent, WALK_SPEED * dt);
        ExploreWalk.Outcome out = ExploreWalk.step(mesh, showingBlocks() ? blocks : null,
                body, move[0], move[1]);
        if (out.moved()) {
            fog.stand(body.cell());
        }
        if (out.cellChanged()) {
            session.record(out.from(), out.to());
        }
        return out;
    }

    /** Living / traffic snapshot — rebuild hulls, keep the body if still legal. */
    public void replace(MazeGrid next) {
        if (next == null) {
            return;
        }
        this.grid = next;
        this.mesh = ExploreMesh.of(next);
        this.markers = ExploreMarkers.plan(next);
        Point here = body.cell();
        if (!next.inBounds(here) || next.openNeighbors(here).isEmpty()
                && !here.equals(next.start())) {
            body.moveTo(ExploreMesh.worldX(next.start().col()),
                    ExploreMesh.worldZ(next.start().row()));
        }
        fog.stand(body.cell());
    }

    public void pulseLive(long tickSeed, boolean harden) {
        replace(ExploreLive.pulse(grid, tickSeed, harden));
    }

    static double yawToward(Direction d) {
        if (d == null) {
            return 0;
        }
        return switch (d) {
            case NORTH -> 0;
            case EAST -> Math.PI / 2;
            case SOUTH -> Math.PI;
            case WEST -> -Math.PI / 2;
        };
    }

    private static void faceFirstOpening(MazeGrid grid, ExploreBody body) {
        Point start = grid.start();
        if (start == null) {
            return;
        }
        for (Direction d : Direction.values()) {
            if (grid.isOpen(start.row(), start.col(), d)) {
                body.look(yawToward(d), 0);
                return;
            }
        }
    }

    public void occupyHere() {
        WeightedMazeGrid weighted = ExploreTraffic.occupy(grid, body.cell());
        if (weighted != null) {
            this.grid = weighted;
        }
    }
}
