// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.List;

/**
 * One extruded dungeon: mesh, body, fog, markers, living replace, traffic.
 */
public final class ExploreWorld {

    public static final int DEFAULT_ROWS = 21;
    public static final int DEFAULT_COLS = 31;
    public static final long DEFAULT_SEED = 7L;
    public static final double WALK_SPEED = 4.2;

    private final String generatorId;
    private final long seed;
    private MazeGrid grid;
    private ExploreMesh mesh;
    private final ExploreBody body;
    private final ExploreFog fog = new ExploreFog();
    private List<ExploreMarker> markers;
    private final ExploreSession session = new ExploreSession();

    public ExploreWorld(String generatorId, long seed, MazeGrid grid) {
        this.generatorId = generatorId == null ? "dungeon" : generatorId;
        this.seed = seed;
        this.grid = grid;
        this.mesh = ExploreMesh.of(grid);
        this.body = ExploreBody.atCell(grid.start());
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
        ExploreInput.applyLook(body, intent);
        double[] move = ExploreInput.moveVector(body, intent, WALK_SPEED * dt);
        ExploreWalk.Outcome out = ExploreWalk.step(mesh, body, move[0], move[1]);
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

    public void occupyHere() {
        WeightedMazeGrid weighted = ExploreTraffic.occupy(grid, body.cell());
        if (weighted != null) {
            this.grid = weighted;
        }
    }
}
