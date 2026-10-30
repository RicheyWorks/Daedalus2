// SPDX-License-Identifier: MIT

package com.daedalus.engine;

/**
 * Marker base for shipped generators. Neighbor helpers used to live here as
 * "OPTIMIZED scaffolding" that no generator (and no plugin) ever called; they
 * were deleted 2026-08-26 so plugin authors are not inheriting dead advice.
 */
public abstract class AbstractMazeGenerator implements MazeGenerator {
}
