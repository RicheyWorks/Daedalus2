// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeMap;

/**
 * A floating voxel island as a pure function of its seed (ADR-018).
 *
 * <p>Ported from the Blender generator ({@code voxel_island.py}) into world coordinates: Y is up,
 * X/Z are the ground plane, the island's top sits a few cubes above its origin and its rocky
 * underside hangs below. Layers top-down are grass (sand at the rim), dirt, then stone. A pond
 * sits off-centre; a stream runs from it to the rim and falls off the cliff as a waterfall.
 * Trees (some in blossom), boulders, crystals under the island and a few clouds finish it.
 *
 * <p>Determinism is the contract: every decision is either {@link IslandNoise} (pure hashing) or
 * one {@link SplittableRandom} drawn in a fixed iteration order. No hash-ordered collection is
 * ever iterated to make a decision. {@link IslandPlan#digest()} pins it in a golden test.
 */
public final class IslandGenerator {

    /** Smallest and largest radius the generator will honour. */
    public static final int MIN_RADIUS = 8;
    public static final int MAX_RADIUS = 28;
    public static final int DEFAULT_RADIUS = 18;
    /** Pier cubes past the rim column (ADR-019). */
    public static final int PIER_LENGTH = 7;

    private static final int WATER_TOP = 3;

    private IslandGenerator() {
    }

    public static IslandPlan generate(long seed) {
        return generate(seed, DEFAULT_RADIUS);
    }

    public static IslandPlan generate(long seed, int radius) {
        if (radius < MIN_RADIUS || radius > MAX_RADIUS) {
            throw new IllegalArgumentException(
                    "Island radius must be " + MIN_RADIUS + ".." + MAX_RADIUS + ", was " + radius);
        }
        return new Build(seed, radius).run();
    }

    /** One generation pass. Mutable scratch; never escapes. */
    private static final class Build {
        final long seed;
        final int radius;
        final IslandNoise noise;
        final SplittableRandom rng;
        final TreeMap<BlockCoordinate, BlockType> blocks = new TreeMap<>(ORDER);
        // Column (x,z) → top surface y, and the normalised distance from centre.
        final TreeMap<Long, Integer> heights = new TreeMap<>();
        final TreeMap<Long, Double> dist = new TreeMap<>();
        final Set<Long> wet = new HashSet<>();
        double pondCx;
        double pondCz;
        double pondR;
        int streamLength;
        boolean waterfall;
        int trees;
        int blossomTrees;
        int crystals;
        int boulders;
        int pondColumns;
        // Pier tip (relative): the cube an ark moors beside. Set by dock().
        int dockX;
        int dockY;
        int dockZ;
        final Set<Long> reserved = new HashSet<>();

        Build(long seed, int radius) {
            this.seed = seed;
            this.radius = radius;
            this.noise = new IslandNoise(seed);
            this.rng = new SplittableRandom(seed);
        }

        IslandPlan run() {
            terrain();
            stream();
            dock();
            int targetTrees = Math.max(3, (int) Math.round(9.0 * radius * radius / 361.0));
            trees(targetTrees);
            boulders(3 + rng.nextInt(3));
            crystals(5 + rng.nextInt(6));
            clouds(2 + rng.nextInt(2));
            int top = Integer.MIN_VALUE;
            int bottom = Integer.MAX_VALUE;
            for (BlockCoordinate c : blocks.keySet()) {
                top = Math.max(top, c.y());
                bottom = Math.min(bottom, c.y());
            }
            IslandTraits traits = new IslandTraits(seed, radius, heights.size(), blocks.size(),
                    trees, blossomTrees, pondColumns, streamLength, waterfall, crystals, boulders,
                    top, bottom, dockX, dockY, dockZ);
            return new IslandPlan(traits, blocks);
        }

        void terrain() {
            double scale = radius / 19.0;
            pondCx = 5 * scale;
            pondCz = -3 * scale;
            pondR = 4.2 * scale;
            int span = radius + 6;
            for (int x = -span; x <= span; x++) {
                for (int z = -span; z <= span; z++) {
                    double n = noise.fractal(x * 0.09, z * 0.09, 1, 2);
                    double d = Math.hypot(x, z) / radius + n * 0.22;
                    if (d >= 1.0) {
                        continue;
                    }
                    double hn = noise.fractal(x * 0.07, z * 0.07, 2, 2);
                    int h = (int) Math.round(3 + (1 - d) * 5 + hn * 3.5);
                    double under = Math.abs(noise.value(x * 0.3, z * 0.3, 3));
                    int bottom = (int) Math.round(-Math.pow(1 - d, 0.6) * 15 - under * 4);
                    double pondWobble = noise.value(x * 0.4, z * 0.4, 4) * 0.8;
                    boolean inPond = Math.hypot(x - pondCx, z - pondCz) < pondR + pondWobble;
                    if (inPond) {
                        h = Math.min(h, WATER_TOP - 1);
                        wet.add(key(x, z));
                        pondColumns++;
                    }
                    bottom = Math.min(bottom, h - 1);
                    heights.put(key(x, z), h);
                    dist.put(key(x, z), d);
                    for (int y = bottom; y <= h; y++) {
                        BlockType t;
                        if (y == h) {
                            t = (inPond || d > 0.88) ? BlockType.SAND : BlockType.GRASS;
                        } else if (y >= h - 2) {
                            t = BlockType.DIRT;
                        } else {
                            t = BlockType.STONE;
                        }
                        blocks.put(new BlockCoordinate(x, y, z), t);
                    }
                    if (inPond) {
                        for (int y = h + 1; y <= WATER_TOP; y++) {
                            blocks.put(new BlockCoordinate(x, y, z), BlockType.WATER);
                        }
                    }
                }
            }
        }

        void stream() {
            int x = (int) Math.round(pondCx);
            int z = (int) Math.round(pondCz);
            List<long[]> path = new ArrayList<>();
            while (heights.containsKey(key(x, z))) {
                path.add(new long[] {x, z});
                x++;
                if (rng.nextDouble() < 0.3) {
                    z += rng.nextBoolean() ? 1 : -1;
                }
            }
            int edgeX = x;
            int edgeZ = z;
            for (long[] step : path) {
                int sx = (int) step[0];
                for (int sz = (int) step[1]; sz <= step[1] + 1; sz++) {
                    Long k = key(sx, sz);
                    Integer h = heights.get(k);
                    if (h == null || wet.contains(k)) {
                        continue;
                    }
                    for (int y = WATER_TOP; y <= h; y++) {
                        blocks.remove(new BlockCoordinate(sx, y, sz));
                    }
                    blocks.put(new BlockCoordinate(sx, WATER_TOP - 1, sz), BlockType.SAND);
                    blocks.put(new BlockCoordinate(sx, WATER_TOP, sz), BlockType.WATER);
                    heights.put(k, WATER_TOP - 1);
                    wet.add(k);
                    streamLength++;
                }
            }
            if (path.isEmpty()) {
                return;
            }
            // The fall hugs the cliff just outside the last stream column and thins at the end.
            waterfall = true;
            for (int fz = edgeZ; fz <= edgeZ + 1; fz++) {
                for (int y = WATER_TOP; y > WATER_TOP - 30; y--) {
                    int drop = WATER_TOP - y;
                    if (drop > 22 && rng.nextDouble() < (drop - 22) / 10.0) {
                        continue;
                    }
                    BlockCoordinate at = new BlockCoordinate(edgeX, y, fz);
                    if (!blocks.containsKey(at)) {
                        blocks.put(at, BlockType.WATER);
                    }
                }
            }
        }

        /**
         * A plank pier off the +Z rim (the side facing the world origin), three cubes wide and
         * {@link IslandGenerator#PIER_LENGTH} long, on log posts. An ark moors at its tip. The
         * pier starts from the rim column nearest x = 0 that is dry, so the stream never floods it.
         */
        void dock() {
            int bestX = 0;
            int bestZ = Integer.MIN_VALUE;
            for (int x = -2; x <= 2; x++) {
                for (Map.Entry<Long, Integer> e : heights.entrySet()) {
                    if (keyX(e.getKey()) != x || wet.contains(e.getKey())) {
                        continue;
                    }
                    int z = keyZ(e.getKey());
                    if (z > bestZ || (z == bestZ && Math.abs(x) < Math.abs(bestX))) {
                        bestZ = z;
                        bestX = x;
                    }
                }
            }
            int deck = heights.get(key(bestX, bestZ));
            for (int z = bestZ - 1; z <= bestZ + PIER_LENGTH; z++) {
                for (int x = bestX - 1; x <= bestX + 1; x++) {
                    reserved.add(key(x, z));
                    BlockCoordinate plank = new BlockCoordinate(x, deck, z);
                    // On land the pier is a plank path laid into the grass; past the rim it floats.
                    blocks.put(plank, BlockType.WOOD);
                    for (int y = deck + 1; y <= deck + 3; y++) {
                        blocks.remove(new BlockCoordinate(x, y, z));
                    }
                }
                if (z > bestZ && (z - bestZ) % 3 == 0) {
                    for (int x : new int[] {bestX - 1, bestX + 1}) {
                        for (int y = deck - 3; y < deck; y++) {
                            BlockCoordinate post = new BlockCoordinate(x, y, z);
                            if (!blocks.containsKey(post)) {
                                blocks.put(post, BlockType.LOG);
                            }
                        }
                    }
                }
            }
            int tip = bestZ + PIER_LENGTH;
            // Mooring bollards at the tip: what a player sees as "the ark ties up here".
            blocks.put(new BlockCoordinate(bestX - 1, deck + 1, tip), BlockType.LOG);
            blocks.put(new BlockCoordinate(bestX + 1, deck + 1, tip), BlockType.LOG);
            dockX = bestX;
            dockY = deck;
            dockZ = tip;
        }

        boolean nearReserved(int x, int z, int pad) {
            for (int dx = -pad; dx <= pad; dx++) {
                for (int dz = -pad; dz <= pad; dz++) {
                    if (reserved.contains(key(x + dx, z + dz))) {
                        return true;
                    }
                }
            }
            return false;
        }

        boolean nearWet(int x, int z, int pad) {
            for (int dx = -pad; dx <= pad; dx++) {
                for (int dz = -pad; dz <= pad; dz++) {
                    if (wet.contains(key(x + dx, z + dz))) {
                        return true;
                    }
                }
            }
            return false;
        }

        void trees(int target) {
            List<Long> spots = new ArrayList<>();
            for (Map.Entry<Long, Double> e : dist.entrySet()) {
                int x = keyX(e.getKey());
                int z = keyZ(e.getKey());
                if (e.getValue() < 0.72 && !nearWet(x, z, 3) && !nearReserved(x, z, 3)) {
                    spots.add(e.getKey());
                }
            }
            shuffle(spots);
            List<int[]> placed = new ArrayList<>();
            for (Long k : spots) {
                if (placed.size() >= target) {
                    break;
                }
                int x = keyX(k);
                int z = keyZ(k);
                boolean clear = true;
                for (int[] p : placed) {
                    int dx = x - p[0];
                    int dz = z - p[1];
                    if (dx * dx + dz * dz <= 40) {
                        clear = false;
                        break;
                    }
                }
                if (!clear) {
                    continue;
                }
                placed.add(new int[] {x, z});
                boolean blossom = placed.size() % 3 == 0;
                tree(x, z, blossom);
                trees++;
                if (blossom) {
                    blossomTrees++;
                }
            }
        }

        void tree(int x, int z, boolean blossom) {
            int base = heights.get(key(x, z)) + 1;
            int trunk = 4 + rng.nextInt(4);
            for (int y = base; y < base + trunk; y++) {
                blocks.put(new BlockCoordinate(x, y, z), BlockType.LOG);
            }
            BlockType leaf = blossom ? BlockType.BLOSSOM : BlockType.LEAVES;
            double r = 2.2 + rng.nextDouble();
            int cy = base + trunk;
            int ri = (int) Math.ceil(r);
            for (int dx = -ri; dx <= ri; dx++) {
                for (int dy = -ri; dy <= ri; dy++) {
                    for (int dz = -ri; dz <= ri; dz++) {
                        double reach = dx * dx + dz * dz + (dy * 1.3) * (dy * 1.3);
                        double wobble = rng.nextDouble() * 2.0 - 1.5;
                        if (reach <= r * r + wobble) {
                            BlockCoordinate at = new BlockCoordinate(x + dx, cy + dy, z + dz);
                            if (!blocks.containsKey(at)) {
                                blocks.put(at, leaf);
                            }
                        }
                    }
                }
            }
        }

        void boulders(int count) {
            List<Long> spots = new ArrayList<>();
            for (Map.Entry<Long, Double> e : dist.entrySet()) {
                int x = keyX(e.getKey());
                int z = keyZ(e.getKey());
                if (e.getValue() > 0.45 && e.getValue() < 0.85 && !nearWet(x, z, 2) && !nearReserved(x, z, 2)
                        && !blocks.containsKey(new BlockCoordinate(x, heights.get(e.getKey()) + 1, z))) {
                    spots.add(e.getKey());
                }
            }
            shuffle(spots);
            for (int i = 0; i < count && i < spots.size(); i++) {
                int x = keyX(spots.get(i));
                int z = keyZ(spots.get(i));
                int base = heights.get(spots.get(i)) + 1;
                int tall = 1 + rng.nextInt(2);
                for (int dx = 0; dx < 2; dx++) {
                    for (int dz = 0; dz < 2; dz++) {
                        for (int dy = 0; dy < tall; dy++) {
                            if (rng.nextDouble() < 0.85) {
                                BlockCoordinate at = new BlockCoordinate(x + dx, base + dy, z + dz);
                                if (!blocks.containsKey(at)) {
                                    blocks.put(at, BlockType.STONE);
                                }
                            }
                        }
                    }
                }
                boulders++;
            }
        }

        void crystals(int count) {
            // Lowest underside columns, deepest first, ties broken by the column key.
            List<long[]> under = new ArrayList<>();
            TreeMap<Long, Integer> lowest = new TreeMap<>();
            for (BlockCoordinate c : blocks.keySet()) {
                Long k = key(c.x(), c.z());
                if (heights.containsKey(k) && c.y() < lowest.getOrDefault(k, Integer.MAX_VALUE)) {
                    lowest.put(k, c.y());
                }
            }
            for (Map.Entry<Long, Integer> e : lowest.entrySet()) {
                under.add(new long[] {e.getKey(), e.getValue()});
            }
            under.sort(Comparator.<long[]>comparingLong(a -> a[1]).thenComparingLong(a -> a[0]));
            List<long[]> pool = new ArrayList<>(under.subList(0, Math.min(60, under.size())));
            for (int i = pool.size() - 1; i > 0; i--) {
                int j = rng.nextInt(i + 1);
                long[] tmp = pool.get(i);
                pool.set(i, pool.get(j));
                pool.set(j, tmp);
            }
            for (int i = 0; i < count && i < pool.size(); i++) {
                int x = keyX(pool.get(i)[0]);
                int z = keyZ(pool.get(i)[0]);
                int y0 = (int) pool.get(i)[1];
                int len = 3 + rng.nextInt(4);
                for (int d = 1; d <= len; d++) {
                    blocks.put(new BlockCoordinate(x, y0 - d, z), BlockType.CRYSTAL);
                }
                crystals++;
            }
        }

        void clouds(int count) {
            for (int i = 0; i < count; i++) {
                double angle = rng.nextDouble() * Math.PI * 2;
                int cx = (int) Math.round(Math.cos(angle) * (radius + 6));
                int cz = (int) Math.round(Math.sin(angle) * (radius + 6));
                int cy = 16 + rng.nextInt(5);
                for (int puff = 0; puff < 4; puff++) {
                    int ox = cx + rng.nextInt(7) - 3;
                    int oz = cz + rng.nextInt(5) - 2;
                    for (int dx = -3; dx <= 3; dx++) {
                        for (int dz = -2; dz <= 2; dz++) {
                            for (int dy = 0; dy <= 1; dy++) {
                                if (dx * dx / 9.0 + dz * dz / 4.0 + dy * dy / 2.0 <= 1.0) {
                                    BlockCoordinate at = new BlockCoordinate(ox + dx, cy + dy, oz + dz);
                                    if (!blocks.containsKey(at)) {
                                        blocks.put(at, BlockType.CLOUD);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        <T> void shuffle(List<T> list) {
            for (int i = list.size() - 1; i > 0; i--) {
                int j = rng.nextInt(i + 1);
                T tmp = list.get(i);
                list.set(i, list.get(j));
                list.set(j, tmp);
            }
        }
    }

    /** Total order on coordinates: y, then z, then x. The plan iterates in this order. */
    static final Comparator<BlockCoordinate> ORDER = Comparator
            .comparingInt(BlockCoordinate::y)
            .thenComparingInt(BlockCoordinate::z)
            .thenComparingInt(BlockCoordinate::x);

    static long key(int x, int z) {
        return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
    }

    static int keyX(long k) {
        return (int) (k >> 32);
    }

    static int keyZ(long k) {
        return (int) k;
    }
}
