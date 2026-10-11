// SPDX-License-Identifier: MIT

package com.daedalus.world.district;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.World;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;
import java.util.TreeMap;

/**
 * A Parcels world's ground (ADR-033): a Decentraland-style district of square plots on a flat plain.
 *
 * <p><b>Layout — the same in every Parcels world.</b> Four by four city blocks, each two by two plots of
 * {@link #PLOT} cubes, with {@link #ROAD}-wide streets between the blocks and a ring road around them:
 * {@link #SIDE} cubes on a side. Plot {@code n = row * 8 + col} (row along +Z, col along +X). The four
 * plots at the district's heart, together with the crossing between them, are the plaza. Its centre holds the
 * helipad the world's helicopter flies from (the Parcels mount, ADR-031). That leaves {@link #CLAIMABLE}
 * plots. The plaza sits on gate 0's line (x = 48), so the flight to the clouds past the rainbow is
 * straight down −Z.
 *
 * <p><b>Ground.</b> Three cubes deep, with the surface at y = 0: grass on plots, asphalt edged with
 * sidewalk on the streets, and paving on the plaza.
 *
 * <p><b>Show plots.</b> The seed decides which plots open with something on them: a grove, a glass
 * pavilion, a tower, a crystal sculpture or a pond. About half are bare lawn, waiting for an owner.
 * Everything a plot holds stays inside it, below {@link #HEIGHT}: the plot is what a claim covers, and
 * the height limit keeps the sky gates out of reach of anything built.
 *
 * <p>Deterministic: one {@code SplittableRandom(seed)} per plot.
 */
public final class DistrictOps {

    public static final int PLOT = 16;
    public static final int ROAD = 4;
    public static final int BLOCKS = 4;
    public static final int PLOTS_PER_SIDE = BLOCKS * 2;
    public static final int SIDE = BLOCKS * 2 * PLOT + (BLOCKS + 1) * ROAD;
    /** West edge (x) and north edge (z): the plaza's centre lands on x = 48, gate 0's line. */
    public static final int MIN_X = -26;
    public static final int MIN_Z = -148;
    /** Ground surface. Plots are claimed from here up to {@link #HEIGHT}. */
    public static final int GROUND_Y = 0;
    public static final int DEPTH = 3;
    /** Highest cube anything on a plot may reach; the gates' rainbows start at y = 55. */
    public static final int HEIGHT = 32;
    /** The helicopter's home slot, past the islands' 0..63 and the gates' 1000..1007. */
    public static final int PAD_SLOT = 2000;
    public static final int PLAZA_LO = 3;
    public static final int PLAZA_HI = 4;
    public static final int CLAIMABLE = PLOTS_PER_SIDE * PLOTS_PER_SIDE - 4;

    /** What the seed put on a plot when the district was laid out. */
    public enum Show { LAWN, GROVE, PAVILION, TOWER, SCULPTURE, POND }

    /** A plot: its number, its claim box and what it opened with. */
    public record Plot(int n, ParcelBounds bounds, Show show) {

        public int centerX() {
            return (bounds.minX() + bounds.maxX() + 1) / 2;
        }

        public int centerZ() {
            return (bounds.minZ() + bounds.maxZ() + 1) / 2;
        }
    }

    /** A whole district: every cube, every plot in number order. */
    public record Plan(Map<BlockCoordinate, BlockType> cubes, List<Plot> plots) {

        public Plan {
            TreeMap<BlockCoordinate, BlockType> copy = new TreeMap<>(DistrictOps::compare);
            copy.putAll(cubes);
            cubes = Collections.unmodifiableMap(copy);
            plots = List.copyOf(plots);
        }
    }

    private DistrictOps() {
    }

    /** x of column {@code col}'s west edge (or z of row {@code row}'s north edge, from {@link #MIN_Z}). */
    static int offset(int i) {
        return ROAD + (i / 2) * (2 * PLOT + ROAD) + (i % 2) * PLOT;
    }

    public static boolean isPlaza(int n) {
        int row = n / PLOTS_PER_SIDE;
        int col = n % PLOTS_PER_SIDE;
        return row >= PLAZA_LO && row <= PLAZA_HI && col >= PLAZA_LO && col <= PLAZA_HI;
    }

    /** True for the plot numbers a person can claim: 0..63 except the plaza's four. */
    public static boolean isPlot(int n) {
        return n >= 0 && n < PLOTS_PER_SIDE * PLOTS_PER_SIDE && !isPlaza(n);
    }

    /** Plot {@code n}'s claim box: its 16 × 16 footprint from the ground to the height limit. */
    public static ParcelBounds plotBounds(int n) {
        if (!isPlot(n)) {
            throw new IllegalArgumentException("No plot " + n);
        }
        int x = MIN_X + offset(n % PLOTS_PER_SIDE);
        int z = MIN_Z + offset(n / PLOTS_PER_SIDE);
        return new ParcelBounds(x, GROUND_Y, z, x + PLOT - 1, HEIGHT, z + PLOT - 1);
    }

    /** The plot whose footprint holds (x, z), or -1 on a street or the plaza. */
    public static int plotAt(int x, int z) {
        for (int n = 0; n < PLOTS_PER_SIDE * PLOTS_PER_SIDE; n++) {
            if (isPlot(n)) {
                ParcelBounds b = plotBounds(n);
                if (x >= b.minX() && x <= b.maxX() && z >= b.minZ() && z <= b.maxZ()) {
                    return n;
                }
            }
        }
        return -1;
    }

    /** The plaza: the four heart plots and the crossing between them. */
    public static ParcelBounds plaza() {
        int lo = offset(PLAZA_LO);
        int hi = offset(PLAZA_HI) + PLOT - 1;
        return new ParcelBounds(MIN_X + lo, GROUND_Y, MIN_Z + lo, MIN_X + hi, GROUND_Y, MIN_Z + hi);
    }

    /** Where the helicopter rests: the cube above the helipad's centre. */
    public static BlockCoordinate padBerth() {
        ParcelBounds p = plaza();
        return new BlockCoordinate((p.minX() + p.maxX() + 1) / 2, GROUND_Y + 1, (p.minZ() + p.maxZ() + 1) / 2);
    }

    /** The district grown from {@code seed}. */
    public static Plan plan(long seed) {
        TreeMap<BlockCoordinate, BlockType> out = new TreeMap<>(DistrictOps::compare);
        ParcelBounds plaza = plaza();
        for (int dx = 0; dx < SIDE; dx++) {
            for (int dz = 0; dz < SIDE; dz++) {
                int x = MIN_X + dx;
                int z = MIN_Z + dz;
                BlockType top = surface(dx, dz, x, z, plaza);
                out.put(new BlockCoordinate(x, GROUND_Y, z), top);
                out.put(new BlockCoordinate(x, GROUND_Y - 1, z), top == BlockType.GRASS ? BlockType.DIRT : BlockType.GRAVEL);
                out.put(new BlockCoordinate(x, GROUND_Y - 2, z), BlockType.STONE);
            }
        }
        helipad(out);
        List<Plot> plots = new ArrayList<>();
        for (int n = 0; n < PLOTS_PER_SIDE * PLOTS_PER_SIDE; n++) {
            if (!isPlot(n)) {
                continue;
            }
            ParcelBounds b = plotBounds(n);
            SplittableRandom rng = new SplittableRandom(seed * 1_000_003L + n);
            Show show = pick(rng);
            dress(out, b, show, rng);
            plots.add(new Plot(n, b, show));
        }
        return new Plan(out, plots);
    }

    private static Show pick(SplittableRandom rng) {
        int r = rng.nextInt(100);
        if (r < 48) {
            return Show.LAWN;
        } else if (r < 66) {
            return Show.GROVE;
        } else if (r < 78) {
            return Show.PAVILION;
        } else if (r < 88) {
            return Show.TOWER;
        } else if (r < 94) {
            return Show.SCULPTURE;
        }
        return Show.POND;
    }

    private static BlockType surface(int dx, int dz, int x, int z, ParcelBounds plaza) {
        if (x >= plaza.minX() && x <= plaza.maxX() && z >= plaza.minZ() && z <= plaza.maxZ()) {
            return BlockType.PAVING;
        }
        int ix = inPlotAxis(dx);
        int iz = inPlotAxis(dz);
        if (ix >= 0 && iz >= 0) {
            return BlockType.GRASS;
        }
        // A street: asphalt, with a sidewalk on each edge that faces a plot.
        int along = ix >= 0 ? dz : dx;      // the coordinate across this street
        int across = streetOffset(along);
        return across == 0 || across == ROAD - 1 ? BlockType.PAVING : BlockType.ROAD;
    }

    /** Position inside a plot along one axis (0..15), or -1 on a street. */
    private static int inPlotAxis(int d) {
        int block = 2 * PLOT + ROAD;
        int r = Math.floorMod(d - ROAD, block);
        if (d < ROAD || d >= SIDE - ROAD || r >= 2 * PLOT) {
            return -1;
        }
        return r % PLOT;
    }

    /** Position across a street (0..ROAD-1). */
    private static int streetOffset(int d) {
        if (d < ROAD) {
            return d;
        }
        if (d >= SIDE - ROAD) {
            return d - (SIDE - ROAD);
        }
        return Math.floorMod(d - ROAD, 2 * PLOT + ROAD) - 2 * PLOT;
    }

    /** An orange square with a paving H, at the plaza's centre. */
    private static void helipad(Map<BlockCoordinate, BlockType> out) {
        BlockCoordinate c = padBerth();
        for (int dx = -5; dx <= 4; dx++) {
            for (int dz = -5; dz <= 4; dz++) {
                boolean h = (dx == -3 || dx == 2) && dz >= -3 && dz <= 2 || (dz == -1 || dz == 0) && dx > -3 && dx < 2;
                out.put(new BlockCoordinate(c.x() + dx, GROUND_Y, c.z() + dz), h ? BlockType.PAVING : BlockType.HELIPAD);
            }
        }
    }

    private static void put(Map<BlockCoordinate, BlockType> out, ParcelBounds b, int x, int y, int z, BlockType t) {
        // Nothing a show plot holds may leave its plot or pass the height limit.
        if (x >= b.minX() && x <= b.maxX() && z >= b.minZ() && z <= b.maxZ() && y >= GROUND_Y && y <= HEIGHT) {
            out.put(new BlockCoordinate(x, y, z), t);
        }
    }

    private static void dress(Map<BlockCoordinate, BlockType> out, ParcelBounds b, Show show, SplittableRandom rng) {
        int x0 = b.minX();
        int z0 = b.minZ();
        int cx = x0 + PLOT / 2;
        int cz = z0 + PLOT / 2;
        switch (show) {
            case LAWN -> {
                for (int i = 0; i < 3; i++) {   // a few flowers in the grass
                    put(out, b, x0 + 2 + rng.nextInt(12), GROUND_Y + 1, z0 + 2 + rng.nextInt(12), BlockType.BLOSSOM);
                }
            }
            case GROVE -> {
                int trees = 2 + rng.nextInt(3);
                for (int t = 0; t < trees; t++) {
                    tree(out, b, x0 + 3 + rng.nextInt(10), z0 + 3 + rng.nextInt(10), 4 + rng.nextInt(3),
                            rng.nextInt(4) == 0 ? BlockType.BLOSSOM : BlockType.LEAVES);
                }
            }
            case PAVILION -> {
                int h = 4;
                for (int dx = -4; dx <= 4; dx++) {
                    for (int dz = -4; dz <= 4; dz++) {
                        put(out, b, cx + dx, GROUND_Y, cz + dz, BlockType.PAVING);
                        boolean post = Math.abs(dx) == 4 && Math.abs(dz) == 4;
                        if (post) {
                            for (int y = 1; y <= h; y++) {
                                put(out, b, cx + dx, GROUND_Y + y, cz + dz, BlockType.WOOD);
                            }
                        }
                        put(out, b, cx + dx, GROUND_Y + h + 1, cz + dz,
                                Math.abs(dx) == 4 || Math.abs(dz) == 4 ? BlockType.WOOD : BlockType.GLASS);
                    }
                }
            }
            case TOWER -> {
                int h = 12 + rng.nextInt(13);
                for (int y = 1; y <= h; y++) {
                    for (int dx = -3; dx <= 3; dx++) {
                        for (int dz = -3; dz <= 3; dz++) {
                            boolean wall = Math.abs(dx) == 3 || Math.abs(dz) == 3;
                            if (!wall) {
                                continue;
                            }
                            boolean corner = Math.abs(dx) == 3 && Math.abs(dz) == 3;
                            boolean window = !corner && y % 4 != 1 && y < h;
                            put(out, b, cx + dx, GROUND_Y + y, cz + dz, window ? BlockType.GLASS : BlockType.STONE);
                        }
                    }
                }
                for (int dx = -3; dx <= 3; dx++) {
                    for (int dz = -3; dz <= 3; dz++) {
                        put(out, b, cx + dx, GROUND_Y + h + 1, cz + dz, BlockType.PAVING);
                    }
                }
            }
            case SCULPTURE -> {
                int h = 8 + rng.nextInt(10);
                for (int y = 1; y <= h; y++) {
                    int r = Math.max(0, 2 - y / 4);
                    for (int dx = -r; dx <= r; dx++) {
                        for (int dz = -r; dz <= r; dz++) {
                            if (dx * dx + dz * dz <= r * r) {
                                put(out, b, cx + dx, GROUND_Y + y, cz + dz, BlockType.CRYSTAL);
                            }
                        }
                    }
                }
                for (int dx = -3; dx <= 3; dx++) {
                    for (int dz = -3; dz <= 3; dz++) {
                        if (dx * dx + dz * dz <= 9) {
                            put(out, b, cx + dx, GROUND_Y, cz + dz, BlockType.PAVING);
                        }
                    }
                }
            }
            case POND -> {
                for (int dx = -4; dx <= 4; dx++) {
                    for (int dz = -3; dz <= 3; dz++) {
                        double e = dx * dx / 16.0 + dz * dz / 9.0;
                        if (e <= 1.0) {
                            put(out, b, cx + dx, GROUND_Y, cz + dz, e <= 0.6 ? BlockType.WATER : BlockType.SAND);
                        }
                    }
                }
                tree(out, b, cx + 5, cz + 4, 5, BlockType.LEAVES);
            }
            default -> throw new IllegalStateException(show.name());
        }
    }

    private static void tree(Map<BlockCoordinate, BlockType> out, ParcelBounds b, int x, int z, int h, BlockType crown) {
        for (int y = 1; y <= h; y++) {
            put(out, b, x, GROUND_Y + y, z, BlockType.LOG);
        }
        for (int dx = -2; dx <= 2; dx++) {
            for (int dy = -1; dy <= 2; dy++) {
                for (int dz = -2; dz <= 2; dz++) {
                    if (dx * dx + dy * dy * 2 + dz * dz <= 5 && !(dx == 0 && dz == 0 && dy < 1)) {
                        put(out, b, x + dx, GROUND_Y + h + dy, z + dz, crown);
                    }
                }
            }
        }
    }

    /** True when every cube of the district is free in {@code world}. */
    public static boolean fits(World world, Plan plan) {
        for (BlockCoordinate at : plan.cubes().keySet()) {
            if (world.get(at).solid()) {
                return false;
            }
        }
        return true;
    }

    /** Lay the district out; false (and nothing placed) when anything is in the way. */
    public static boolean build(World world, Plan plan) {
        if (!fits(world, plan)) {
            return false;
        }
        plan.cubes().forEach(world::place);
        return true;
    }

    private static int compare(BlockCoordinate a, BlockCoordinate b) {
        int y = Integer.compare(a.y(), b.y());
        if (y != 0) {
            return y;
        }
        int z = Integer.compare(a.z(), b.z());
        return z != 0 ? z : Integer.compare(a.x(), b.x());
    }
}
