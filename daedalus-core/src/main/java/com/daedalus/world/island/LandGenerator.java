// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;
import java.util.TreeMap;

/**
 * A land (ADR-050): a large, deep piece of the shattered world, as a pure function of its seed.
 *
 * <p>The story: the biggest world in the galaxy was hit by a meteor; its pieces float in a bubble, and people live
 * on them. A land is one of those pieces, up to 92 cubes across (a Sandbox LAND is 96), fitting the island claim
 * box (ADR-026) so ownership, leases and slots work unchanged. From the top down:
 * <ul>
 *   <li>grass hills (sand at the rim and the lake), a lake whose stream falls off the edge as a waterfall, trees;</li>
 *   <li>dirt, then STONE, then DEEPSTONE below about 16 down, hanging under the land like an upturned mountain
 *       up to 46 deep, with fracture faces where it broke off;</li>
 *   <li>caves winding through the rock;</li>
 *   <li>ore veins by depth: coal (shallow), copper, iron, gold (deep), crystal geodes in the deep caves;</li>
 *   <li>a HEARTSTONE core at the bottom, glowing, that holds the piece up in the bubble (it can't be mined).</li>
 * </ul>
 * Every land rolls its {@link Richness} from its seed: most are {@code COMMON}, a quarter {@code RICH} (more ore,
 * more gold), one in twenty {@code LEGENDARY}: the meteor struck there, leaving a crater and STARMETAL under it. You
 * never know until you dig, or survey.
 *
 * <p>Deterministic like {@link IslandGenerator}: hashing noise plus one {@link SplittableRandom} drawn in a fixed
 * order; cubes kept in {@link IslandGenerator#ORDER}.
 */
public final class LandGenerator {

    public static final int MIN_RADIUS = 32;
    public static final int MAX_RADIUS = 46;
    /** Cubes stay within this many of the origin sideways (the claim box is 47) and below (48). */
    static final int MAX_REACH = 46;

    public enum Richness { COMMON, RICH, LEGENDARY }

    private LandGenerator() {
    }

    /** What a land holds, by its seed alone (the same roll the generator makes first). */
    public static Richness richness(long seed) {
        double roll = new SplittableRandom(seed ^ 0x5EED1A9DL).nextDouble();
        return roll < 0.70 ? Richness.COMMON : roll < 0.95 ? Richness.RICH : Richness.LEGENDARY;
    }

    public static IslandPlan generate(long seed, int radius) {
        if (radius < MIN_RADIUS || radius > MAX_RADIUS) {
            throw new IllegalArgumentException("Land radius must be " + MIN_RADIUS + ".." + MAX_RADIUS + ", was " + radius);
        }
        return new Build(seed, radius).run();
    }

    /** Counts of each cube type in a plan: what's there to find. */
    public static Map<BlockType, Integer> survey(IslandPlan plan) {
        Map<BlockType, Integer> out = new TreeMap<>();
        for (BlockType t : plan.blocks().values()) {
            out.merge(t, 1, Integer::sum);
        }
        return out;
    }

    private static final class Build {
        final long seed;
        final int radius;
        final Richness richness;
        final IslandNoise noise;
        final SplittableRandom rng;
        final TreeMap<BlockCoordinate, BlockType> blocks = new TreeMap<>(IslandGenerator.ORDER);
        final TreeMap<Long, Integer> heights = new TreeMap<>();
        final TreeMap<Long, Integer> bottoms = new TreeMap<>();
        final TreeMap<Long, Double> dist = new TreeMap<>();
        final List<double[]> cuts = new ArrayList<>();
        double lakeX;
        double lakeZ;
        double lakeR;
        int waterTop;
        int pondColumns;
        int streamLength;
        boolean waterfall;
        int trees;
        int blossomTrees;
        int crystals;
        int boulders;
        int dockX;
        int dockY;
        int dockZ;
        double craterX;
        double craterZ;

        Build(long seed, int radius) {
            this.seed = seed;
            this.radius = radius;
            this.richness = richness(seed);
            this.noise = new IslandNoise(seed);
            this.rng = new SplittableRandom(seed);
        }

        IslandPlan run() {
            fractures();
            lake();
            if (richness == Richness.LEGENDARY) {
                double a = rng.nextDouble() * Math.PI * 2;
                double r = radius * (0.25 + rng.nextDouble() * 0.25);
                craterX = Math.cos(a) * r;
                craterZ = Math.sin(a) * r;
            }
            terrain();
            caves();
            stream();
            ores();
            heart();
            if (richness == Richness.LEGENDARY) {
                meteor();
            }
            dock();
            trees(Math.max(12, heights.size() / 190));
            boulders(6 + rng.nextInt(6));
            int top = Integer.MIN_VALUE;
            int bottom = Integer.MAX_VALUE;
            for (BlockCoordinate c : blocks.keySet()) {
                top = Math.max(top, c.y());
                bottom = Math.min(bottom, c.y());
            }
            IslandTraits traits = new IslandTraits(seed, radius, heights.size(), blocks.size(), trees, blossomTrees,
                    pondColumns, streamLength, waterfall, crystals, boulders, top, bottom, dockX, dockY, dockZ);
            return new IslandPlan(traits, blocks);
        }

        /** Two or three straight breaks where this piece split from the world: cliff faces. */
        void fractures() {
            int n = 2 + rng.nextInt(2);
            double start = rng.nextDouble() * Math.PI * 2;
            for (int i = 0; i < n; i++) {
                double angle = start + i * (Math.PI * 2 / n) + (rng.nextDouble() - 0.5) * 0.8;
                double reach = radius * (0.72 + rng.nextDouble() * 0.2);
                cuts.add(new double[] {Math.cos(angle), Math.sin(angle), reach});
            }
        }

        void lake() {
            double a = rng.nextDouble() * Math.PI * 2;
            double r = radius * (0.15 + rng.nextDouble() * 0.3);
            lakeX = Math.cos(a) * r;
            lakeZ = Math.sin(a) * r;
            lakeR = 4.5 + rng.nextDouble() * 3.5;
        }

        boolean inside(int x, int z) {
            if (Math.abs(x) > MAX_REACH || Math.abs(z) > MAX_REACH) {
                return false;
            }
            double d = Math.hypot(x, z) / radius + noise.fractal(x * 0.05, z * 0.05, 1, 3) * 0.22;
            if (d >= 1.0) {
                return false;
            }
            for (double[] c : cuts) {
                if (x * c[0] + z * c[1] > c[2] + noise.value(x * 0.2, z * 0.2, 5) * 2.0) {
                    return false;
                }
            }
            dist.put(IslandGenerator.key(x, z), d);
            return true;
        }

        void terrain() {
            // Surface first, so the lake's level is known.
            for (int x = -MAX_REACH; x <= MAX_REACH; x++) {
                for (int z = -MAX_REACH; z <= MAX_REACH; z++) {
                    if (!inside(x, z)) {
                        continue;
                    }
                    double d = dist.get(IslandGenerator.key(x, z));
                    double hills = noise.fractal(x * 0.035, z * 0.035, 2, 3);
                    int h = (int) Math.round(6 + hills * 7 + (1 - d) * 3);
                    if (richness == Richness.LEGENDARY) {
                        double cd = Math.hypot(x - craterX, z - craterZ);
                        if (cd < 9) {
                            h -= (int) Math.round((9 - cd) * 0.8);       // the bowl the meteor left
                        } else if (cd < 11) {
                            h += 1;                                      // its raised lip
                        }
                    }
                    heights.put(IslandGenerator.key(x, z), Math.min(h, 22));
                }
            }
            Integer lakeFloor = heights.get(IslandGenerator.key((int) Math.round(lakeX), (int) Math.round(lakeZ)));
            waterTop = lakeFloor == null ? 4 : lakeFloor;
            for (Map.Entry<Long, Integer> e : heights.entrySet()) {
                int x = IslandGenerator.keyX(e.getKey());
                int z = IslandGenerator.keyZ(e.getKey());
                double d = dist.get(e.getKey());
                int h = e.getValue();
                boolean inLake = Math.hypot(x - lakeX, z - lakeZ) < lakeR + noise.value(x * 0.4, z * 0.4, 4);
                if (inLake) {
                    h = Math.min(h, waterTop - 2 - (int) Math.round(Math.max(0, lakeR - Math.hypot(x - lakeX, z - lakeZ)) * 0.4));
                    pondColumns++;
                }
                // The upturned mountain beneath: deepest in the middle, thin at the rim.
                double under = Math.abs(noise.value(x * 0.12, z * 0.12, 3));
                int depth = (int) Math.round(Math.pow(Math.max(0, 1 - d), 0.55) * (34 + radius / 4.0) + under * 6);
                int bottom = Math.max(-MAX_REACH, Math.min(h - 2, -depth));
                heights.put(e.getKey(), h);
                bottoms.put(e.getKey(), bottom);
                int dirt = 2 + (int) Math.round(Math.abs(noise.value(x * 0.3, z * 0.3, 6)) * 2);
                int deep = -16 + (int) Math.round(noise.value(x * 0.08, z * 0.08, 7) * 4);
                for (int y = bottom; y <= h; y++) {
                    BlockType t;
                    if (y == h) {
                        t = (inLake || d > 0.93) ? BlockType.SAND : BlockType.GRASS;
                    } else if (y >= h - dirt) {
                        t = inLake ? BlockType.SAND : BlockType.DIRT;
                    } else if (y > deep) {
                        t = BlockType.STONE;
                    } else {
                        t = BlockType.DEEPSTONE;
                    }
                    blocks.put(new BlockCoordinate(x, y, z), t);
                }
                if (inLake) {
                    for (int y = h + 1; y <= waterTop; y++) {
                        blocks.put(new BlockCoordinate(x, y, z), BlockType.WATER);
                    }
                }
            }
        }

        /** 3-D value noise in about [-1, 1] (hashing per lattice corner, like IslandNoise). */
        double value3(double x, double y, double z, int channel) {
            int x0 = (int) Math.floor(x);
            int y0 = (int) Math.floor(y);
            int z0 = (int) Math.floor(z);
            double fx = smooth(x - x0);
            double fy = smooth(y - y0);
            double fz = smooth(z - z0);
            double c00 = lerp(lat(x0, y0, z0, channel), lat(x0 + 1, y0, z0, channel), fx);
            double c10 = lerp(lat(x0, y0 + 1, z0, channel), lat(x0 + 1, y0 + 1, z0, channel), fx);
            double c01 = lerp(lat(x0, y0, z0 + 1, channel), lat(x0 + 1, y0, z0 + 1, channel), fx);
            double c11 = lerp(lat(x0, y0 + 1, z0 + 1, channel), lat(x0 + 1, y0 + 1, z0 + 1, channel), fx);
            return lerp(lerp(c00, c10, fy), lerp(c01, c11, fy), fz);
        }

        double lat(int x, int y, int z, int channel) {
            long h = seed;
            h ^= (long) x * 0x9E3779B97F4A7C15L;
            h ^= (long) y * 0xD6E8FEB86659FD93L;
            h ^= (long) z * 0xC2B2AE3D27D4EB4FL;
            h ^= (long) channel * 0x165667B19E3779F9L;
            h = IslandNoise.mix(h);
            return ((h >>> 11) * 0x1.0p-53) * 2.0 - 1.0;
        }

        static double smooth(double t) {
            return t * t * (3 - 2 * t);
        }

        static double lerp(double a, double b, double t) {
            return a + (b - a) * t;
        }

        /** Winding tunnels: where two noise fields both sit near zero, a worm of air. */
        void caves() {
            List<BlockCoordinate> carve = new ArrayList<>();
            for (Map.Entry<BlockCoordinate, BlockType> e : blocks.entrySet()) {
                BlockCoordinate c = e.getKey();
                BlockType t = e.getValue();
                if (t != BlockType.STONE && t != BlockType.DEEPSTONE) {
                    continue;
                }
                long k = IslandGenerator.key(c.x(), c.z());
                int h = heights.get(k);
                int bottom = bottoms.get(k);
                if (c.y() > h - 6 || c.y() < bottom + 4) {
                    continue;
                }
                double a = value3(c.x() * 0.06, c.y() * 0.09, c.z() * 0.06, 11);
                double b = value3(c.x() * 0.06, c.y() * 0.09, c.z() * 0.06, 12);
                if (Math.abs(a) < 0.07 && Math.abs(b) < 0.11) {
                    carve.add(c);
                }
            }
            for (BlockCoordinate c : carve) {
                blocks.remove(c);
            }
        }

        /** From the lake to the nearest rim, then off the edge as a waterfall. */
        void stream() {
            double best = Double.MAX_VALUE;
            double dirX = 1;
            double dirZ = 0;
            for (int i = 0; i < 16; i++) {
                double a = i * Math.PI / 8;
                double cx = Math.cos(a);
                double cz = Math.sin(a);
                int steps = 0;
                double x = lakeX;
                double z = lakeZ;
                while (heights.containsKey(IslandGenerator.key((int) Math.round(x), (int) Math.round(z))) && steps < 200) {
                    x += cx;
                    z += cz;
                    steps++;
                }
                if (steps < best) {
                    best = steps;
                    dirX = cx;
                    dirZ = cz;
                }
            }
            double x = lakeX;
            double z = lakeZ;
            int lastX = 0;
            int lastZ = 0;
            boolean any = false;
            while (true) {
                int ix = (int) Math.round(x);
                int iz = (int) Math.round(z);
                long k = IslandGenerator.key(ix, iz);
                if (!heights.containsKey(k)) {
                    break;
                }
                int h = heights.get(k);
                if (h >= waterTop) {
                    for (int y = waterTop; y <= h; y++) {
                        blocks.remove(new BlockCoordinate(ix, y, iz));
                    }
                    blocks.put(new BlockCoordinate(ix, waterTop - 1, iz), BlockType.SAND);
                    blocks.put(new BlockCoordinate(ix, waterTop, iz), BlockType.WATER);
                    heights.put(k, waterTop - 1);
                    streamLength++;
                }
                lastX = ix;
                lastZ = iz;
                any = true;
                x += dirX;
                z += dirZ;
            }
            if (!any) {
                return;
            }
            // The fall: just past the last stream cube, down the cliff face, thinning out near the bottom.
            int fx = (int) Math.round(lastX + dirX);
            int fz = (int) Math.round(lastZ + dirZ);
            if (Math.abs(fx) > MAX_REACH || Math.abs(fz) > MAX_REACH) {
                return;
            }
            waterfall = true;
            for (int y = waterTop; y > -MAX_REACH; y--) {
                int drop = waterTop - y;
                if (drop > 34 && rng.nextDouble() < (drop - 34) / 10.0) {
                    continue;
                }
                BlockCoordinate at = new BlockCoordinate(fx, y, fz);
                if (!blocks.containsKey(at)) {
                    blocks.put(at, BlockType.WATER);
                }
            }
        }

        /** Ore veins, by depth band; a rich land has more of everything and much more gold. */
        void ores() {
            int rock = 0;
            for (BlockType t : blocks.values()) {
                if (t == BlockType.STONE || t == BlockType.DEEPSTONE) {
                    rock++;
                }
            }
            double mult = richness == Richness.COMMON ? 1.0 : richness == Richness.RICH ? 2.2 : 3.0;
            double goldMult = richness == Richness.COMMON ? 1.0 : 3.0;
            vein(BlockType.COAL_ORE, -22, -2, rock / 10000.0 * 14 * mult, 6, 14);
            vein(BlockType.COPPER_ORE, -28, -6, rock / 10000.0 * 10 * mult, 5, 11);
            vein(BlockType.IRON_ORE, -38, -14, rock / 10000.0 * 7 * mult, 4, 9);
            vein(BlockType.GOLD_ORE, -46, -26, rock / 10000.0 * 2.5 * mult * goldMult, 3, 7);
            geodes((int) Math.round(rock / 10000.0 * 2 * mult) + 1);
        }

        void vein(BlockType ore, int yMin, int yMax, double count, int minLen, int maxLen) {
            int veins = (int) Math.round(count);
            List<Long> columns = new ArrayList<>(heights.keySet());
            for (int v = 0; v < veins; v++) {
                // A start in rock within the band: a few tries, then give up on this vein.
                for (int attempt = 0; attempt < 12; attempt++) {
                    long k = columns.get(rng.nextInt(columns.size()));
                    int x = IslandGenerator.keyX(k);
                    int z = IslandGenerator.keyZ(k);
                    int y = yMin + rng.nextInt(yMax - yMin + 1);
                    if (!isRock(x, y, z)) {
                        continue;
                    }
                    int len = minLen + rng.nextInt(maxLen - minLen + 1);
                    for (int i = 0; i < len; i++) {
                        if (isRock(x, y, z)) {
                            blocks.put(new BlockCoordinate(x, y, z), ore);
                        }
                        switch (rng.nextInt(6)) {
                            case 0 -> x++;
                            case 1 -> x--;
                            case 2 -> z++;
                            case 3 -> z--;
                            case 4 -> y++;
                            default -> y--;
                        }
                    }
                    break;
                }
            }
        }

        boolean isRock(int x, int y, int z) {
            BlockType t = blocks.get(new BlockCoordinate(x, y, z));
            return t == BlockType.STONE || t == BlockType.DEEPSTONE;
        }

        /** Crystal clusters on deep cave walls. */
        void geodes(int count) {
            List<BlockCoordinate> walls = new ArrayList<>();
            for (BlockCoordinate c : blocks.keySet()) {
                if (c.y() < -18 && blocks.get(c) == BlockType.DEEPSTONE
                        && !blocks.containsKey(new BlockCoordinate(c.x(), c.y() + 1, c.z()))
                        && heights.containsKey(IslandGenerator.key(c.x(), c.z()))
                        && c.y() + 1 < heights.get(IslandGenerator.key(c.x(), c.z())) - 6) {
                    walls.add(c);   // a deep cave floor
                }
            }
            for (int i = 0; i < count && !walls.isEmpty(); i++) {
                BlockCoordinate c = walls.get(rng.nextInt(walls.size()));
                int tall = 1 + rng.nextInt(3);
                for (int dy = 1; dy <= tall; dy++) {
                    BlockCoordinate at = new BlockCoordinate(c.x(), c.y() + dy, c.z());
                    if (!blocks.containsKey(at)) {
                        blocks.put(at, BlockType.CRYSTAL);
                    }
                }
                crystals++;
            }
        }

        /** The glowing core at the bottom of the middle: what holds the piece up. */
        void heart() {
            int lowest = 0;
            long at = IslandGenerator.key(0, 0);
            for (Map.Entry<Long, Integer> e : bottoms.entrySet()) {
                if (e.getValue() < lowest || (e.getValue() == lowest && Math.abs(IslandGenerator.keyX(e.getKey())) + Math.abs(IslandGenerator.keyZ(e.getKey()))
                        < Math.abs(IslandGenerator.keyX(at)) + Math.abs(IslandGenerator.keyZ(at)))) {
                    lowest = e.getValue();
                    at = e.getKey();
                }
            }
            int hx = IslandGenerator.keyX(at);
            int hz = IslandGenerator.keyZ(at);
            int hy = lowest + 4;
            for (int dx = -3; dx <= 3; dx++) {
                for (int dy = -3; dy <= 3; dy++) {
                    for (int dz = -3; dz <= 3; dz++) {
                        if (dx * dx + dy * dy + dz * dz <= 9) {
                            BlockCoordinate c = new BlockCoordinate(hx + dx, hy + dy, hz + dz);
                            if (blocks.containsKey(c)) {
                                blocks.put(c, BlockType.HEARTSTONE);
                            }
                        }
                    }
                }
            }
        }

        /** The meteor's leavings: a starmetal mass under the crater, and veins of it spreading down. */
        void meteor() {
            int cx = (int) Math.round(craterX);
            int cz = (int) Math.round(craterZ);
            Integer floor = heights.get(IslandGenerator.key(cx, cz));
            if (floor == null) {
                return;
            }
            int cy = floor - 5;
            for (int dx = -3; dx <= 3; dx++) {
                for (int dy = -3; dy <= 3; dy++) {
                    for (int dz = -3; dz <= 3; dz++) {
                        double reach = dx * dx + dy * dy * 1.4 + dz * dz;
                        if (reach <= 9 + noise.value((cx + dx) * 0.7, (cz + dz) * 0.7, 9) * 3) {
                            BlockCoordinate c = new BlockCoordinate(cx + dx, cy + dy, cz + dz);
                            if (blocks.containsKey(c)) {
                                blocks.put(c, BlockType.STARMETAL);
                            }
                        }
                    }
                }
            }
            vein(BlockType.STARMETAL, Math.max(-MAX_REACH, cy - 20), cy - 2, 6, 4, 9);
        }

        /** A short plank dock at the rim nearest +Z, inside the claim box: an ark moors at its tip. */
        void dock() {
            int bestX = 0;
            int bestZ = Integer.MIN_VALUE;
            for (int x = -2; x <= 2; x++) {
                for (Map.Entry<Long, Integer> e : heights.entrySet()) {
                    if (IslandGenerator.keyX(e.getKey()) != x) {
                        continue;
                    }
                    int z = IslandGenerator.keyZ(e.getKey());
                    if (z > bestZ) {
                        bestZ = z;
                        bestX = x;
                    }
                }
            }
            int deck = heights.get(IslandGenerator.key(bestX, bestZ));
            int tip = Math.min(bestZ + 3, MAX_REACH);
            for (int z = bestZ - 2; z <= tip; z++) {
                for (int x = bestX - 1; x <= bestX + 1; x++) {
                    blocks.put(new BlockCoordinate(x, deck, z), BlockType.WOOD);
                    for (int y = deck + 1; y <= deck + 3; y++) {
                        blocks.remove(new BlockCoordinate(x, y, z));
                    }
                }
            }
            blocks.put(new BlockCoordinate(bestX - 1, deck + 1, tip), BlockType.LOG);
            blocks.put(new BlockCoordinate(bestX + 1, deck + 1, tip), BlockType.LOG);
            dockX = bestX;
            dockY = deck;
            dockZ = tip;
        }

        void trees(int target) {
            List<Long> spots = new ArrayList<>();
            for (Map.Entry<Long, Double> e : dist.entrySet()) {
                Integer h = heights.get(e.getKey());
                if (h == null || e.getValue() > 0.8) {
                    continue;
                }
                BlockType top = blocks.get(new BlockCoordinate(IslandGenerator.keyX(e.getKey()), h, IslandGenerator.keyZ(e.getKey())));
                if (top == BlockType.GRASS) {
                    spots.add(e.getKey());
                }
            }
            for (int i = spots.size() - 1; i > 0; i--) {
                int j = rng.nextInt(i + 1);
                Long tmp = spots.get(i);
                spots.set(i, spots.get(j));
                spots.set(j, tmp);
            }
            List<int[]> placed = new ArrayList<>();
            for (Long k : spots) {
                if (placed.size() >= target) {
                    break;
                }
                int x = IslandGenerator.keyX(k);
                int z = IslandGenerator.keyZ(k);
                boolean clear = Math.abs(x - dockX) > 3 || Math.abs(z - dockZ) > 6;
                for (int[] p : placed) {
                    if ((x - p[0]) * (x - p[0]) + (z - p[1]) * (z - p[1]) <= 30) {
                        clear = false;
                        break;
                    }
                }
                if (!clear) {
                    continue;
                }
                placed.add(new int[] {x, z});
                boolean blossom = placed.size() % 4 == 0;
                int base = heights.get(k) + 1;
                int trunk = 4 + rng.nextInt(4);
                for (int y = base; y < base + trunk; y++) {
                    blocks.put(new BlockCoordinate(x, y, z), BlockType.LOG);
                }
                BlockType leaf = blossom ? BlockType.BLOSSOM : BlockType.LEAVES;
                double r = 2.2 + rng.nextDouble();
                int ri = (int) Math.ceil(r);
                int cy = base + trunk;
                for (int dx = -ri; dx <= ri; dx++) {
                    for (int dy = -ri; dy <= ri; dy++) {
                        for (int dz = -ri; dz <= ri; dz++) {
                            double reach = dx * dx + dz * dz + (dy * 1.3) * (dy * 1.3);
                            if (reach <= r * r + rng.nextDouble() * 2.0 - 1.5
                                    && Math.abs(x + dx) <= MAX_REACH && Math.abs(z + dz) <= MAX_REACH) {
                                BlockCoordinate at = new BlockCoordinate(x + dx, cy + dy, z + dz);
                                if (!blocks.containsKey(at)) {
                                    blocks.put(at, leaf);
                                }
                            }
                        }
                    }
                }
                trees++;
                if (blossom) {
                    blossomTrees++;
                }
            }
        }

        void boulders(int count) {
            List<Long> spots = new ArrayList<>();
            for (Map.Entry<Long, Double> e : dist.entrySet()) {
                Integer h = heights.get(e.getKey());
                if (h != null && e.getValue() > 0.4 && e.getValue() < 0.85
                        && blocks.get(new BlockCoordinate(IslandGenerator.keyX(e.getKey()), h, IslandGenerator.keyZ(e.getKey()))) == BlockType.GRASS
                        && !blocks.containsKey(new BlockCoordinate(IslandGenerator.keyX(e.getKey()), h + 1, IslandGenerator.keyZ(e.getKey())))) {
                    spots.add(e.getKey());
                }
            }
            for (int i = 0; i < count && !spots.isEmpty(); i++) {
                long k = spots.get(rng.nextInt(spots.size()));
                int x = IslandGenerator.keyX(k);
                int z = IslandGenerator.keyZ(k);
                int base = heights.get(k) + 1;
                for (int dx = 0; dx < 2; dx++) {
                    for (int dz = 0; dz < 2; dz++) {
                        for (int dy = 0; dy < 2; dy++) {
                            BlockCoordinate at = new BlockCoordinate(x + dx, base + dy, z + dz);
                            if (rng.nextDouble() < 0.8 && !blocks.containsKey(at) && Math.abs(x + dx) <= MAX_REACH && Math.abs(z + dz) <= MAX_REACH) {
                                blocks.put(at, BlockType.STONE);
                            }
                        }
                    }
                }
                boulders++;
            }
        }
    }
}
