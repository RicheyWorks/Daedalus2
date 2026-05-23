// SPDX-License-Identifier: MIT

package com.daedalus.engine;

import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;

/**
 * SPI for any maze generation algorithm. Implementations should:
 *
 * <ul>
 *   <li>be deterministic given a seed — same seed ⇒ same maze</li>
 *   <li>produce a perfect maze (single connected component, no loops) unless their
 *       theoretical contract says otherwise (e.g. flawed/braid variants)</li>
 *   <li>accumulate stats into the supplied {@link MazeStats} as they run</li>
 * </ul>
 *
 * <p>Plugins contribute generators by implementing this interface and registering them
 * via {@code MazePlugin#registerAlgorithms}. Built-ins are wired in {@code AlgorithmConfig}.
 */
public interface MazeGenerator {

    /** Stable identifier (e.g. {@code "recursive-backtracker"}) — used in REST APIs and the UI. */
    String id();

    /** Human-friendly name. */
    String displayName();

    /** Descriptor surfaced to UI / REST consumers. */
    AlgorithmDescriptor descriptor();

    /** Generate a maze of the given dimensions seeded by {@code seed}. */
    MazeGrid generate(int rows, int cols, long seed, MazeStats stats);

    default MazeGrid generate(int rows, int cols, long seed) {
        return generate(rows, cols, seed, new MazeStats());
    }

    default MazeGrid generate(int rows, int cols) {
        return generate(rows, cols, System.nanoTime(), new MazeStats());
    }
}
