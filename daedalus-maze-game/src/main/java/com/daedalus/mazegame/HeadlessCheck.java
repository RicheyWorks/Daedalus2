// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;

import java.io.PrintStream;
import java.util.List;

/**
 * Headless self-check for CI and deploy smoke tests: builds every tier for one seed, walks the
 * BFS route through the real rules, and prints one line per tier. Returns the failure count.
 */
public final class HeadlessCheck {

    private HeadlessCheck() {
    }

    public static int run(long seed, MazeFactory factory, PrintStream out) {
        out.println("Labyrinth Run headless check, seed " + seed);
        int failures = 0;
        for (Difficulty d : Difficulty.values()) {
            MazeRun run = new MazeRun(seed, d, factory);
            List<Point> route = run.ghost("bfs");
            for (int i = 1; i < route.size(); i++) {
                run.move(MazeGrid.directionBetween(route.get(i - 1), route.get(i)));
            }
            boolean ok = run.isWon() && run.moves() == run.par();
            if (!ok) {
                failures++;
            }
            out.printf("%-14s %-6s %2dx%-2d par %3d hash %s stars %d %s%n", run.shareCode(), d, run.size(), run.size(),
                    run.par(), run.mazeHash(), run.stars(Scoring.parMillis(run.par())), ok ? "OK" : "FAIL");
        }
        out.println(failures == 0 ? "ALL TIERS SOLVABLE" : failures + " TIER(S) FAILED");
        return failures;
    }
}
