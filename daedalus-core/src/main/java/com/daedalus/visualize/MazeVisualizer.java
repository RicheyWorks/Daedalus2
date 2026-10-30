// SPDX-License-Identifier: MIT

package com.daedalus.visualize;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;

import java.util.List;

/**
 * Rendering contract for a maze plus its run statistics (audit recommendation §2.1.1).
 *
 * <p>The engine already knows how to project a {@link MazeGrid} into a glyph grid
 * ({@code MazeGrid#toTileGrid}); what was missing was a seam a front end can implement without
 * inventing its own projection. JavaFX, a web canvas, and a terminal each implement this once;
 * everything upstream (services, plugins, examples) renders through the interface and stays
 * ignorant of the target. {@link AsciiMazeVisualizer} is the reference implementation and the
 * one the engine itself uses for {@code MazeGrid#toString()}.
 *
 * <p>Kept deliberately small — a render target, not a scene graph. Implementations that need
 * incremental redraw (a live web canvas following STOMP frames) should subscribe to the frame
 * topics instead; this contract is for whole-state snapshots.
 */
public interface MazeVisualizer {

    /**
     * Render the grid, optionally overlaying a solver path.
     *
     * @param grid  the maze to render
     * @param stats run statistics to display alongside, or {@code null} for none
     * @param path  solver path to overlay in cell coordinates, empty for none
     */
    void render(MazeGrid grid, MazeStats stats, List<Point> path);

    /** Render without a path overlay. */
    default void render(MazeGrid grid, MazeStats stats) {
        render(grid, stats, List.of());
    }
}
