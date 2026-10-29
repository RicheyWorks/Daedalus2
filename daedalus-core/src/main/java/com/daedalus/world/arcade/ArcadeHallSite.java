// SPDX-License-Identifier: MIT

package com.daedalus.world.arcade;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;
import com.daedalus.world.island.IslandPlan;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/**
 * Where an arcade hall (and its entrance path) could stand on a generated island. A pure, read-only function of an
 * {@link IslandPlan}: it never edits the plan and nothing in island generation calls it, so every generated island stays
 * byte-identical (pinned by {@code ArcadeHallSiteTest} against {@code IslandGeneratorTest.GOLDEN_SEED_11}).
 *
 * <p>Placement is opt-in: {@link #siteIfEnabled} returns empty unless the system property {@value #FLAG} is
 * {@code true} (default off). {@link #find} itself is always available to tools and tests.
 *
 * <p>Rule: the hall footprint ({@code cellsW*2} x {@code cellsD*2} columns, +X wide, +Z deep) plus a 2-column approach strip
 * {@link #approachLength()} long in front of the doorway (-Z) must all be land (top cube grass, sand or dirt: no water,
 * trees, crystals, boulders, pier planks) and the footprint top may vary by at most {@link #MAX_STEP} cube (the 0.4 m
 * foundation absorbs it). Among valid spots the one whose footprint centre is closest to the island origin wins; ties
 * break on z, then x, so the answer is deterministic.
 */
public final class ArcadeHallSite {

    /** System property that turns island hall placement on. Off by default. */
    public static final String FLAG = "daedalus.arcadeHall.islandSites";
    /** Largest allowed difference in top height across the hall footprint, cubes. */
    public static final int MAX_STEP = 1;

    private static final Set<BlockType> LAND = EnumSet.of(BlockType.GRASS, BlockType.SAND, BlockType.DIRT);

    /** A chosen site, relative to the island origin. {@code doorAnchor} is the block the player stands on at the threshold. */
    public record Site(String layoutId, int minX, int minZ, int width, int depth, int floorY, BlockCoordinate doorAnchor,
            BlockCoordinate pathStart) {
    }

    private ArcadeHallSite() {
    }

    public static boolean enabled() {
        return Boolean.getBoolean(FLAG);
    }

    /** Columns of steps + path in front of the doorway (same rounding as {@link ArcadeHall#pathStart()}). */
    public static int approachLength() {
        return (int) Math.ceil(ArcadeHall.STEPS_RUN_M + ArcadeHall.PATH_TILES * ArcadeHall.PATH_TILE_M);
    }

    /** {@link #find} when {@value #FLAG} is on, otherwise empty. */
    public static Optional<Site> siteIfEnabled(IslandPlan plan, ArcadeHall.Layout layout) {
        return enabled() ? find(plan, layout) : Optional.empty();
    }

    /** Best site for {@code layout} on {@code plan}, or empty if the island has no flat enough land for it. */
    public static Optional<Site> find(IslandPlan plan, ArcadeHall.Layout layout) {
        Map<Long, Integer> topY = new HashMap<>();
        Map<Long, BlockType> topT = new HashMap<>();
        int x0 = Integer.MAX_VALUE, x1 = Integer.MIN_VALUE, z0 = Integer.MAX_VALUE, z1 = Integer.MIN_VALUE;
        for (Map.Entry<BlockCoordinate, BlockType> e : plan.blocks().entrySet()) {     // ORDER is y-first, so the last cube seen per column is its top
            BlockCoordinate c = e.getKey();
            long k = key(c.x(), c.z());
            topY.put(k, c.y());
            topT.put(k, e.getValue());
            x0 = Math.min(x0, c.x()); x1 = Math.max(x1, c.x()); z0 = Math.min(z0, c.z()); z1 = Math.max(z1, c.z());
        }
        int w = layout.widthM(), d = layout.depthM(), run = approachLength();
        int doorDx = (int) Math.floor(layout.doorX());
        Site best = null;
        long bestD = Long.MAX_VALUE;
        for (int mz = z0 + run; mz + d - 1 <= z1; mz++) {
            for (int mx = x0; mx + w - 1 <= x1; mx++) {
                int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
                boolean ok = true;
                for (int z = mz; z < mz + d && ok; z++) {
                    for (int x = mx; x < mx + w; x++) {
                        long k = key(x, z);
                        if (!LAND.contains(topT.get(k))) {
                            ok = false;
                            break;
                        }
                        int y = topY.get(k);
                        lo = Math.min(lo, y);
                        hi = Math.max(hi, y);
                    }
                }
                if (!ok || hi - lo > MAX_STEP) {
                    continue;
                }
                int dx = mx + doorDx;
                for (int z = mz - run; z < mz && ok; z++) {
                    for (int x = dx - 1; x <= dx; x++) {
                        long k = key(x, z);
                        ok = LAND.contains(topT.get(k)) && Math.abs(topY.get(k) - hi) <= MAX_STEP + 1;
                        if (!ok) {
                            break;
                        }
                    }
                }
                if (!ok) {
                    continue;
                }
                long cx = 2L * mx + w, cz = 2L * mz + d;     // footprint centre x2, to stay in integers
                long dist = cx * cx + cz * cz;
                if (dist < bestD) {
                    bestD = dist;
                    best = new Site(layout.id(), mx, mz, w, d, hi + 1, new BlockCoordinate(dx, hi + 1, mz), new BlockCoordinate(dx, hi + 1, mz - run));
                }
            }
        }
        return Optional.ofNullable(best);
    }

    private static long key(int x, int z) {
        return ((long) x << 32) ^ (z & 0xffffffffL);
    }
}
