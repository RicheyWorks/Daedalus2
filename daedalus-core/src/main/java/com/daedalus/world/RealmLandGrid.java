// SPDX-License-Identifier: MIT
package com.daedalus.world;

/** Proposed ADR-065 default placement only. Never interprets a deed after a tug. */
public final class RealmLandGrid {
    public static final int SIDE = 100;
    public static final int COUNT = SIDE * SIDE;
    public static final int PITCH_CM = 12_800;
    private static final Cell[] CELLS = build();
    private RealmLandGrid() {}

    /** Runtime geometry, deliberately separate from immutable NFT seed/radius. */
    public record Layout(int pitchCm, int clearanceCm) {
        public Layout {
            if (pitchCm < 100 || pitchCm > 1_000_000 || clearanceCm < 0 || clearanceCm >= pitchCm)
                throw new IllegalArgumentException("invalid layout dimensions");
        }
        public int offsetXcm(Cell cell) { return cell.x() * pitchCm; }
        public int offsetZcm(Cell cell) { return cell.z() * pitchCm; }
        public boolean fits(int widthCm, int depthCm) {
            return widthCm > 0 && depthCm > 0 && widthCm <= pitchCm - clearanceCm;
        }
        public boolean canGrow(int oldWidthCm, int oldDepthCm, int widthCm, int depthCm) {
            return fits(oldWidthCm, oldDepthCm) && fits(widthCm, depthCm)
                    && widthCm >= oldWidthCm && depthCm >= oldDepthCm;
        }
    }
    public static final Layout LEGACY_LAYOUT = new Layout(12_800, 3_600);
    public static final Layout EXPANSION_LAYOUT = new Layout(51_200, 1_600);

    /** Logical X/Z plane; Unreal maps logical Z to horizontal Y. */
    public record Cell(int x, int z) {
        public Cell {
            if (x < -49 || x > 50 || z < -49 || z > 50) {
                throw new IllegalArgumentException("cell outside 100x100 realm grid");
            }
        }
        public int district() { return ((z + 49) / 10) * 10 + (x + 49) / 10; }
        public int offsetXcm() { return x * PITCH_CM; }
        public int offsetZcm() { return z * PITCH_CM; }
        public boolean fitsSquare(int side) {
            return side >= 1 && side <= 10 && x + side - 1 <= 50 && z + side - 1 <= 50
                    && (x + 49) / 10 == (x + 49 + side - 1) / 10
                    && (z + 49) / 10 == (z + 49 + side - 1) / 10;
        }
    }

    public static Cell defaultCell(int number) {
        if (number < 0 || number >= COUNT) throw new IllegalArgumentException("land number outside 0..9999");
        return CELLS[number];
    }

    private static Cell[] build() {
        Cell[] cells = new Cell[COUNT];
        int count = 1, x = 0, z = 0, direction = 0;
        cells[0] = new Cell(0, 0);
        int[] dx = {1, 0, -1, 0}, dz = {0, 1, 0, -1};
        for (int length = 1; count < COUNT; length++) {
            for (int repeat = 0; repeat < 2 && count < COUNT; repeat++) {
                for (int step = 0; step < length && count < COUNT; step++) {
                    x += dx[direction]; z += dz[direction];
                    if (x >= -49 && x <= 50 && z >= -49 && z <= 50) cells[count++] = new Cell(x, z);
                }
                direction = (direction + 1) % 4;
            }
        }
        return cells;
    }
}
