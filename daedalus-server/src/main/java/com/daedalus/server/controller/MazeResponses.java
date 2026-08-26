// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.GenerateResponse;
import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.TileType;

import java.util.List;
import java.util.TreeMap;
import java.util.UUID;

/**
 * Shared presentation for maze JSON. Lived on {@link MazeController} until the
 * session and leaderboard surfaces moved out; generate, daily, and breed still
 * need the same glyph flattening and parent-hotspot union.
 */
final class MazeResponses {

    private MazeResponses() {
    }

    static GenerateResponse toResponse(UUID id, String generatorId, int rows, int cols,
                                       long seed, MazeGrid grid, List<Hotspot> hotspots,
                                       Double braid) {
        TileType[][] tiles = grid.toTileGrid();
        char[][] glyphs = new char[tiles.length][];
        for (int r = 0; r < tiles.length; r++) {
            glyphs[r] = new char[tiles[r].length];
            for (int c = 0; c < tiles[r].length; c++) {
                glyphs[r][c] = tiles[r][c].glyph();
            }
        }
        return new GenerateResponse(id, generatorId, rows, cols, seed, glyphs, hotspots, braid);
    }

    /**
     * Union of parent weights, row-major, max cost on a shared cell. Generate accepts
     * at most 64 hotspots; a pair of full lists would otherwise overflow that contract.
     */
    static List<Hotspot> mergeParentHotspots(List<Hotspot> a, List<Hotspot> b) {
        if ((a == null || a.isEmpty()) && (b == null || b.isEmpty())) {
            return null;
        }
        TreeMap<String, Hotspot> byCell = new TreeMap<>();
        for (Hotspot h : a == null ? List.<Hotspot>of() : a) {
            byCell.merge(String.format("%04d,%04d", h.row(), h.col()), h,
                    (x, y) -> x.cost() >= y.cost() ? x : y);
        }
        for (Hotspot h : b == null ? List.<Hotspot>of() : b) {
            byCell.merge(String.format("%04d,%04d", h.row(), h.col()), h,
                    (x, y) -> x.cost() >= y.cost() ? x : y);
        }
        return byCell.values().stream().limit(64).toList();
    }
}
