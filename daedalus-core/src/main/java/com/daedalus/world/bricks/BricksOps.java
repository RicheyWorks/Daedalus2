// SPDX-License-Identifier: MIT

package com.daedalus.world.bricks;

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
 * A Bricks world's ground (ADR-034): the Roblox look. The baseplate is a {@link #SIDE}-square grey plate
 * that is two cubes thick, with its top at y = 0. On it stand a spawn pad, a runway with the world's plane,
 * and an obby: a seeded run of floating bricks over a lava floor, with checkpoints, ending on a gold
 * finish.
 *
 * <p><b>The obby is always beatable.</b> Every jump fits inside the avatar's reach: at most
 * {@link #MAX_GAP} cubes of air straight ahead ({@link #MAX_REACH} with a step to the side), and at most
 * one cube up. The obby test checks this for every platform of many seeds, so the generator cannot drift
 * into an impossible course.
 *
 * <p><b>Building is a sandbox, with three things kept safe:</b> the baseplate itself, the obby corridor
 * (with its spawn), and the runway. Anywhere else above the baseplate is free to build, up to
 * {@link #HEIGHT}. Off the plate there is nothing to build on, so the sky gates stay a flight away.
 *
 * <p>Deterministic: the obby uses one {@code SplittableRandom(seed)}. The plate, spawn and runway are
 * the same in every Bricks world.
 */
public final class BricksOps {

    public static final int SIDE = 128;
    public static final int MIN_X = -16;
    public static final int MIN_Z = -136;
    public static final int TOP_Y = 0;
    /** Highest cube anyone may place; the gates' rainbows start at y = 55. */
    public static final int HEIGHT = 48;
    /** Furthest gap, in cubes of air, between two platforms of the obby, straight ahead. */
    public static final int MAX_GAP = 2;
    /** Furthest reach of a jump, diagonals included: two ahead and one to the side. */
    public static final double MAX_REACH = Math.sqrt(5.0);
    public static final int PLATFORMS = 18;
    /** Every sixth platform is a checkpoint, the last one included. */
    public static final int CHECKPOINT_EVERY = 6;

    /** The obby's corridor: x 2..38 along the plate's west side, z from the spawn north to the finish. */
    public static final int CORRIDOR_MIN_X = 2;
    public static final int CORRIDOR_MAX_X = 38;
    static final int SPAWN_X = 20;
    static final int SPAWN_Z = -24;
    static final int RUNWAY_X = 48;

    /** One brick of the obby: its footprint and the y of its top. */
    public record Platform(int minX, int minZ, int maxX, int maxZ, int y, BlockType type, boolean checkpoint) {

        /** Cubes of air between this footprint and {@code o}'s, along the ground (0 when they touch). */
        public double gapTo(Platform o) {
            int dx = Math.max(0, Math.max(o.minX - maxX - 1, minX - o.maxX - 1));
            int dz = Math.max(0, Math.max(o.minZ - maxZ - 1, minZ - o.maxZ - 1));
            return Math.sqrt(dx * dx + dz * dz);
        }

        /** The cube an avatar stands on to start from here: the middle of the top. */
        public BlockCoordinate standOn() {
            return new BlockCoordinate((minX + maxX + 1) / 2, y + 1, (minZ + maxZ + 1) / 2);
        }
    }

    /** A whole Bricks ground: every cube, and the obby in order from spawn to finish. */
    public record Plan(Map<BlockCoordinate, BlockType> cubes, List<Platform> obby, Platform finish) {

        public Plan {
            TreeMap<BlockCoordinate, BlockType> copy = new TreeMap<>(BricksOps::compare);
            copy.putAll(cubes);
            cubes = Collections.unmodifiableMap(copy);
            obby = List.copyOf(obby);
        }

        /** Where an avatar stands after touching lava past platform {@code reached}: the last checkpoint. */
        public BlockCoordinate respawnAfter(int reached) {
            BlockCoordinate at = spawn();
            for (int i = 0; i <= reached && i < obby.size(); i++) {
                if (obby.get(i).checkpoint()) {
                    at = obby.get(i).standOn();
                }
            }
            return at;
        }
    }

    private BricksOps() {
    }

    /** Where everyone appears: on the spawn pad. */
    public static BlockCoordinate spawn() {
        return new BlockCoordinate(SPAWN_X, TOP_Y + 2, SPAWN_Z);
    }

    /** Where the plane rests: on the runway, which lies on gate 0's line so the climb runs straight. */
    public static BlockCoordinate hangarBerth() {
        return new BlockCoordinate(RUNWAY_X, TOP_Y + 2, -30);
    }

    /** The runway's footprint (white, with a yellow centre line). */
    public static ParcelBounds runway() {
        return new ParcelBounds(RUNWAY_X - 5, TOP_Y + 1, -60, RUNWAY_X + 5, TOP_Y + 1, -12);
    }

    /** The spawn pad's footprint. */
    public static ParcelBounds spawnPad() {
        return new ParcelBounds(SPAWN_X - 3, TOP_Y + 1, SPAWN_Z - 3, SPAWN_X + 3, TOP_Y + 1, SPAWN_Z + 3);
    }

    /** The obby corridor (spawn to finish, lava floor to the height limit). */
    public static ParcelBounds corridor() {
        return new ParcelBounds(CORRIDOR_MIN_X, TOP_Y + 1, MIN_Z + 2, CORRIDOR_MAX_X, HEIGHT, SPAWN_Z + 3);
    }

    /**
     * True when nobody may change the cube at {@code at}: off the plate, the plate itself, above the height
     * limit, the obby (corridor and spawn), or the runway and the air the plane needs above it.
     */
    public static boolean protects(BlockCoordinate at) {
        if (at.x() < MIN_X || at.x() >= MIN_X + SIDE || at.z() < MIN_Z || at.z() >= MIN_Z + SIDE) {
            return true;
        }
        if (at.y() <= TOP_Y || at.y() > HEIGHT) {
            return true;
        }
        ParcelBounds r = runway();
        boolean overRunway = at.x() >= r.minX() && at.x() <= r.maxX() && at.z() >= r.minZ() && at.z() <= r.maxZ();
        return corridor().contains(at) || overRunway;
    }

    /** The Bricks ground with the obby grown from {@code seed}. */
    public static Plan plan(long seed) {
        TreeMap<BlockCoordinate, BlockType> out = new TreeMap<>(BricksOps::compare);
        for (int x = MIN_X; x < MIN_X + SIDE; x++) {
            for (int z = MIN_Z; z < MIN_Z + SIDE; z++) {
                out.put(new BlockCoordinate(x, TOP_Y, z), BlockType.BASEPLATE);
                out.put(new BlockCoordinate(x, TOP_Y - 1, z), BlockType.BASEPLATE);
            }
        }
        ParcelBounds pad = spawnPad();
        fill(out, pad, BlockType.SPAWN);
        ParcelBounds r = runway();
        for (int x = r.minX(); x <= r.maxX(); x++) {
            for (int z = r.minZ(); z <= r.maxZ(); z++) {
                boolean stripe = x == RUNWAY_X && Math.floorMod(z, 6) < 3;
                out.put(new BlockCoordinate(x, r.minY(), z), stripe ? BlockType.BRICK_YELLOW : BlockType.BRICK_WHITE);
            }
        }
        // The obby's floor is lava, from just past the spawn to the finish.
        ParcelBounds c = corridor();
        for (int x = c.minX(); x <= c.maxX(); x++) {
            for (int z = c.minZ(); z < pad.minZ() - 1; z++) {
                out.put(new BlockCoordinate(x, TOP_Y + 1, z), BlockType.LAVA);
            }
        }
        List<Platform> obby = obby(seed);
        for (Platform p : obby) {
            fill(out, new ParcelBounds(p.minX(), p.y(), p.minZ(), p.maxX(), p.y(), p.maxZ()), p.type());
        }
        Platform last = obby.get(obby.size() - 1);
        // The finish: six by six of gold, one more jump of two from the last checkpoint, with a trophy.
        Platform finish = new Platform(last.minX() - 2, last.minZ() - 2 - 6, last.minX() + 3, last.minZ() - 3,
                last.y(), BlockType.BRICK_YELLOW, false);
        fill(out, new ParcelBounds(finish.minX(), finish.y(), finish.minZ(), finish.maxX(), finish.y(), finish.maxZ()),
                BlockType.BRICK_YELLOW);
        BlockCoordinate cup = finish.standOn();
        for (int y = 0; y < 3; y++) {
            out.put(new BlockCoordinate(cup.x(), cup.y() + y, cup.z() - 1), y == 2 ? BlockType.CRYSTAL : BlockType.BRICK_YELLOW);
        }
        return new Plan(out, obby, finish);
    }

    /** The obby's platforms from the spawn's north edge toward the finish. */
    static List<Platform> obby(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x0BB1L);
        BlockType[] colors = {BlockType.BRICK_RED, BlockType.BRICK_BLUE, BlockType.BRICK_GREEN, BlockType.BRICK_YELLOW};
        List<Platform> out = new ArrayList<>();
        int cx = SPAWN_X;
        int y = spawnPad().minY();         // the spawn pad's top; the first brick is one up from it
        int edge = spawnPad().minZ();      // north edge of the last thing stood on
        for (int i = 0; i < PLATFORMS; i++) {
            boolean checkpoint = (i + 1) % CHECKPOINT_EVERY == 0;
            int size = checkpoint ? 4 : 1 + rng.nextInt(3);          // 1..3 square, checkpoints 4
            int gap = 1 + rng.nextInt(MAX_GAP);                      // 1..2 cubes of air
            int rise = i == 0 || rng.nextInt(3) != 0 ? 1 : 0;      // up out of the lava, then mostly climbing
            // Drift left or right: two to the side after a short gap, at most one after a long one.
            int shift = gap == MAX_GAP ? rng.nextInt(3) - 1 : rng.nextInt(5) - 2;
            cx = Math.max(CORRIDOR_MIN_X + 3, Math.min(CORRIDOR_MAX_X - 3, cx + shift));
            int maxZ = edge - 1 - gap;
            int minZ = maxZ - size + 1;
            int minX = cx - size / 2;
            y = Math.min(HEIGHT - 8, y + rise);
            out.add(new Platform(minX, minZ, minX + size - 1, maxZ, y,
                    checkpoint ? BlockType.SPAWN : colors[rng.nextInt(colors.length)], checkpoint));
            edge = minZ;
        }
        return out;
    }

    private static void fill(Map<BlockCoordinate, BlockType> out, ParcelBounds b, BlockType t) {
        for (int x = b.minX(); x <= b.maxX(); x++) {
            for (int y = b.minY(); y <= b.maxY(); y++) {
                for (int z = b.minZ(); z <= b.maxZ(); z++) {
                    out.put(new BlockCoordinate(x, y, z), t);
                }
            }
        }
    }

    /** True when every cube of the plan is free in {@code world}. */
    public static boolean fits(World world, Plan plan) {
        for (BlockCoordinate at : plan.cubes().keySet()) {
            if (world.get(at).solid()) {
                return false;
            }
        }
        return true;
    }

    /** Lay the Bricks ground out; false (and nothing placed) when anything is in the way. */
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
