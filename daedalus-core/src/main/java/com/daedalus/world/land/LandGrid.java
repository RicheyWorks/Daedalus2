// SPDX-License-Identifier: MIT
package com.daedalus.world.land;

import java.util.ArrayList;
import java.util.List;

/** ADR-065 addressing, shared with DaedalusLandGrid.h. This assigns cells, not ownership. */
public final class LandGrid {
    public static final int SIDE = 100;
    public static final int COUNT = SIDE * SIDE;
    public static final int HUB = SIDE / 2;
    public static final int DISTRICT_SIDE = 10;
    public static final double PITCH_M = 256.0;
    private static final Cell INVALID = new Cell(-1, -1);
    private static final List<Cell> TABLE = build();
    private static final int[] INVERSE = inverse();

    private LandGrid() { }

    public record Cell(int x, int y) { }
    /** Horizontal realm metres: +east, +north. Convert explicitly to each engine's axes. */
    public record Metres(double east, double north) { }

    private static List<Cell> build() {
        List<Cell> cells = new ArrayList<>(COUNT);
        cells.add(new Cell(HUB, HUB));
        for (int r = 1; cells.size() < COUNT; r++) {
            for (int y = HUB - r + 1; y <= HUB + r; y++) add(cells, HUB + r, y);
            for (int x = HUB + r - 1; x >= HUB - r; x--) add(cells, x, HUB + r);
            for (int y = HUB + r - 1; y >= HUB - r; y--) add(cells, HUB - r, y);
            for (int x = HUB - r + 1; x <= HUB + r; x++) add(cells, x, HUB - r);
        }
        return List.copyOf(cells);
    }

    private static void add(List<Cell> cells, int x, int y) {
        if (validCell(x, y) && cells.size() < COUNT) cells.add(new Cell(x, y));
    }

    private static int[] inverse() {
        int[] result = new int[COUNT];
        for (int n = 0; n < COUNT; n++) {
            Cell c = TABLE.get(n);
            result[c.y() * SIDE + c.x()] = n;
        }
        return result;
    }

    public static boolean valid(int number) { return number >= 0 && number < COUNT; }
    private static boolean validCell(int x, int y) { return x >= 0 && x < SIDE && y >= 0 && y < SIDE; }
    public static Cell cell(int number) { return valid(number) ? TABLE.get(number) : INVALID; }
    public static int number(int x, int y) { return validCell(x, y) ? INVERSE[y * SIDE + x] : -1; }

    public static int ring(int number) {
        Cell c = cell(number);
        return c.x() < 0 ? -1 : Math.max(Math.abs(c.x() - HUB), Math.abs(c.y() - HUB));
    }

    public static int district(int number) {
        Cell c = cell(number);
        return districtOfCell(c.x(), c.y());
    }

    public static int districtOfCell(int x, int y) {
        return validCell(x, y) ? (y / DISTRICT_SIDE) * DISTRICT_SIDE + x / DISTRICT_SIDE : -1;
    }

    /** Lowest covered land number; invalid/off-grid/cross-district estates return -1. */
    public static int estate(int x, int y, int size) {
        // Subtraction avoids overflow for hostile coordinates.
        if (size < 1 || size > 4 || x < 0 || y < 0 || x > SIDE - size || y > SIDE - size) return -1;
        int district = districtOfCell(x, y);
        if (districtOfCell(x + size - 1, y + size - 1) != district) return -1;
        int lowest = COUNT;
        for (int j = 0; j < size; j++) {
            for (int i = 0; i < size; i++) lowest = Math.min(lowest, number(x + i, y + j));
        }
        return lowest;
    }

    public static Metres metres(int number) { return metres(number, PITCH_M); }
    public static Metres metres(int number, double pitch) {
        requirePitch(pitch);
        Cell c = cell(number);
        if (c.x() < 0) throw new IllegalArgumentException("Land number must be 0..9999");
        return new Metres((c.x() - HUB) * pitch, (c.y() - HUB) * pitch);
    }

    public static int numberAtMetres(double east, double north) { return numberAtMetres(east, north, PITCH_M); }
    public static int numberAtMetres(double east, double north, double pitch) {
        requirePitch(pitch);
        if (!Double.isFinite(east) || !Double.isFinite(north)) return -1;
        double x = Math.floor(east / pitch + 0.5) + HUB;
        double y = Math.floor(north / pitch + 0.5) + HUB;
        if (x < 0 || x >= SIDE || y < 0 || y >= SIDE) return -1;
        return number((int) x, (int) y);
    }

    private static void requirePitch(double pitch) {
        if (!Double.isFinite(pitch) || pitch <= 0 || pitch > Double.MAX_VALUE / SIDE) {
            throw new IllegalArgumentException("Pitch must be finite, positive and representable across the grid");
        }
    }
}
