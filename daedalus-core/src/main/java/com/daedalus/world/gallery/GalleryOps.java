// SPDX-License-Identifier: MIT

package com.daedalus.world.gallery;

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
 * A Gallery City's ground (ADR-035): the Cryptovoxels look.
 *
 * <p><b>Layout — the same in every Gallery City.</b> Five by five city blocks of {@link #BLOCK} cubes,
 * with named streets {@link #STREET} wide between them. The middle block is the Origin plaza, with a drone
 * pad and the Origin spire. Each of the other 24 blocks is cut into parcels by a fixed pattern: four
 * squares, two wide halves, or two deep halves. Each parcel has an address on its nearest street.
 * Height limits fall away from the centre, as downtown does: the inner ring of blocks may build to
 * {@link #HEIGHT_DOWNTOWN}, the outer ring to {@link #HEIGHT_OUTSKIRTS}.
 *
 * <p><b>Galleries.</b> The seed opens some parcels with a white gallery: a glass roof, a glass front
 * facing the street with a door in it, and art hung on the three inner walls. Each frame is a
 * {@link Frame}: a seed for {@link com.daedalus.world.art.MazeArt} and a place on a wall. Everything a
 * gallery holds stays inside its parcel and under the parcel's height.
 */
public final class GalleryOps {

    public static final int BLOCK = 24;
    public static final int STREET = 6;
    public static final int BLOCKS = 5;
    public static final int SIDE = BLOCKS * BLOCK + (BLOCKS + 1) * STREET;
    /** The plaza's centre falls on x = 48, gate 0's line. */
    public static final int MIN_X = -30;
    public static final int MIN_Z = -158;
    public static final int GROUND_Y = 0;
    public static final int HEIGHT_DOWNTOWN = 32;
    public static final int HEIGHT_OUTSKIRTS = 20;
    public static final int MAX_FRAME = 6;
    /** Art seeds run 0..999,999,999: a number a person can read off a frame, and exact in every JSON client. */
    public static final int MAX_SEED = 1_000_000_000;
    /** Street names, west to east (x) and north to south (z), ring roads first and last. */
    private static final List<String> AVENUES = List.of("Ash Lane", "Pixel Street", "Origin Way", "Gallery Row",
            "Voxel Avenue", "Frame Road");
    private static final List<String> STREETS = List.of("North Rim", "Canvas Street", "Plinth Road", "Easel Street",
            "Lantern Way", "South Rim");

    /** Which way a frame faces: the direction from its wall into the room it hangs in. */
    public enum Facing {
        NORTH(0, -1), SOUTH(0, 1), EAST(1, 0), WEST(-1, 0);

        public final int dx;
        public final int dz;

        Facing(int dx, int dz) {
            this.dx = dx;
            this.dz = dz;
        }

        /** The wall's horizontal axis: frames on north/south faces run along x, others along z. */
        public boolean alongX() {
            return dz != 0;
        }
    }

    /**
     * A picture on a wall. {@code x, y, z} is the wall cube at the frame's lowest corner (smallest x or z
     * along the wall); it spans {@code w} cubes along the wall and {@code h} up, on the face toward
     * {@code facing}. {@code seed} picks the maze it shows.
     */
    public record Frame(int x, int y, int z, Facing facing, int w, int h, long seed) {

        /** Every wall cube the frame covers. */
        public List<BlockCoordinate> wall() {
            List<BlockCoordinate> out = new ArrayList<>();
            for (int i = 0; i < w; i++) {
                for (int j = 0; j < h; j++) {
                    out.add(facing.alongX() ? new BlockCoordinate(x + i, y + j, z) : new BlockCoordinate(x, y + j, z + i));
                }
            }
            return out;
        }

        /** True when the two frames cover a common wall face. */
        public boolean overlaps(Frame o) {
            if (o.facing != facing) {
                return false;
            }
            for (BlockCoordinate a : wall()) {
                if (o.wall().contains(a)) {
                    return true;
                }
            }
            return false;
        }
    }

    /** A parcel: its number, its claim box (ground to its height), its address, and whether it opened as a gallery. */
    public record Parcel(int n, ParcelBounds bounds, String address, boolean gallery) {
    }

    /** A named street, as its centreline from (x1, z1) to (x2, z2). */
    public record Street(String name, int x1, int z1, int x2, int z2) {
    }

    /** A whole Gallery City: every cube, every parcel, the galleries' frames, the streets. */
    public record Plan(Map<BlockCoordinate, BlockType> cubes, List<Parcel> parcels, List<Frame> frames, List<Street> streets) {

        public Plan {
            TreeMap<BlockCoordinate, BlockType> copy = new TreeMap<>(GalleryOps::compare);
            copy.putAll(cubes);
            cubes = Collections.unmodifiableMap(copy);
            parcels = List.copyOf(parcels);
            frames = List.copyOf(frames);
            streets = List.copyOf(streets);
        }
    }

    private GalleryOps() {
    }

    static int blockX(int bx) {
        return MIN_X + STREET + bx * (BLOCK + STREET);
    }

    static int blockZ(int bz) {
        return MIN_Z + STREET + bz * (BLOCK + STREET);
    }

    /** The Origin plaza: the middle block. */
    public static ParcelBounds plaza() {
        int x = blockX(BLOCKS / 2);
        int z = blockZ(BLOCKS / 2);
        return new ParcelBounds(x, GROUND_Y, z, x + BLOCK - 1, GROUND_Y, z + BLOCK - 1);
    }

    /** Where the drone rests: the cube over the pad at the plaza's centre. */
    public static BlockCoordinate padBerth() {
        ParcelBounds p = plaza();
        return new BlockCoordinate((p.minX() + p.maxX() + 1) / 2, GROUND_Y + 1, (p.minZ() + p.maxZ() + 1) / 2);
    }

    private static final List<Parcel> PARCELS = layout();

    /** Every parcel, numbered block by block (north to south, west to east), in the same place in every city. */
    public static List<Parcel> parcels() {
        return List.copyOf(PARCELS);                 // immutable already: this returns the same list
    }

    private static List<Parcel> layout() {
        List<Parcel> out = new ArrayList<>();
        int n = 0;
        for (int bz = 0; bz < BLOCKS; bz++) {
            for (int bx = 0; bx < BLOCKS; bx++) {
                if (bx == BLOCKS / 2 && bz == BLOCKS / 2) {
                    continue;
                }
                int height = Math.max(Math.abs(bx - BLOCKS / 2), Math.abs(bz - BLOCKS / 2)) <= 1
                        ? HEIGHT_DOWNTOWN : HEIGHT_OUTSKIRTS;
                int x = blockX(bx);
                int z = blockZ(bz);
                int half = BLOCK / 2;
                List<int[]> cuts = switch ((bx * 3 + bz * 5) % 3) {
                    case 0 -> List.of(new int[] {0, 0, half, half}, new int[] {half, 0, half, half},
                            new int[] {0, half, half, half}, new int[] {half, half, half, half});
                    case 1 -> List.of(new int[] {0, 0, BLOCK, half}, new int[] {0, half, BLOCK, half});
                    default -> List.of(new int[] {0, 0, half, BLOCK}, new int[] {half, 0, half, BLOCK});
                };
                for (int[] c : cuts) {
                    ParcelBounds b = new ParcelBounds(x + c[0], GROUND_Y, z + c[1], x + c[0] + c[2] - 1, height,
                            z + c[1] + c[3] - 1);
                    out.add(new Parcel(n, b, address(n, b), false));
                    n++;
                }
            }
        }
        return List.copyOf(out);
    }

    /** Parcel {@code n}'s claim box, or null when there is no such parcel. */
    public static ParcelBounds parcelBounds(int n) {
        List<Parcel> all = parcels();
        return n >= 0 && n < all.size() ? all.get(n).bounds() : null;
    }

    public static int parcelCount() {
        return parcels().size();
    }

    /** The parcel whose footprint holds (x, z), or -1 on a street or the plaza. */
    public static int parcelAt(int x, int z) {
        for (Parcel p : parcels()) {
            ParcelBounds b = p.bounds();
            if (x >= b.minX() && x <= b.maxX() && z >= b.minZ() && z <= b.maxZ()) {
                return p.n();
            }
        }
        return -1;
    }

    /** Every street's centreline: the avenues run north–south, the streets east–west. */
    public static List<Street> streets() {
        List<Street> out = new ArrayList<>();
        int far = SIDE - 1;
        for (int i = 0; i <= BLOCKS; i++) {
            int x = MIN_X + i * (BLOCK + STREET) + STREET / 2;
            out.add(new Street(AVENUES.get(i), x, MIN_Z, x, MIN_Z + far));
            int z = MIN_Z + i * (BLOCK + STREET) + STREET / 2;
            out.add(new Street(STREETS.get(i), MIN_X, z, MIN_X + far, z));
        }
        return out;
    }

    /** The side of the parcel nearest a street centreline, as the facing a front door would have. */
    static Facing front(ParcelBounds b) {
        Facing best = Facing.NORTH;
        int bestD = Integer.MAX_VALUE;
        for (Street s : streets()) {
            int d;
            Facing f;
            if (s.x1() == s.x2()) {
                int west = b.minX() - s.x1();
                int east = s.x1() - b.maxX();
                d = west > 0 ? west : east > 0 ? east : Integer.MAX_VALUE;
                f = west > 0 ? Facing.WEST : Facing.EAST;
            } else {
                int north = b.minZ() - s.z1();
                int south = s.z1() - b.maxZ();
                d = north > 0 ? north : south > 0 ? south : Integer.MAX_VALUE;
                f = north > 0 ? Facing.NORTH : Facing.SOUTH;
            }
            if (d < bestD) {
                bestD = d;
                best = f;
            }
        }
        return best;
    }

    static String address(int n, ParcelBounds b) {
        Facing f = front(b);
        String name = null;
        int bestD = Integer.MAX_VALUE;
        for (Street s : streets()) {
            boolean avenue = s.x1() == s.x2();
            if (avenue != (f == Facing.EAST || f == Facing.WEST)) {
                continue;
            }
            int d = avenue ? Math.min(Math.abs(b.minX() - s.x1()), Math.abs(b.maxX() - s.x1()))
                    : Math.min(Math.abs(b.minZ() - s.z1()), Math.abs(b.maxZ() - s.z1()));
            if (d < bestD) {
                bestD = d;
                name = s.name();
            }
        }
        return (n + 1) + " " + name;
    }

    /** The city grown from {@code seed}: which parcels open as galleries, and what hangs in them. */
    public static Plan plan(long seed) {
        TreeMap<BlockCoordinate, BlockType> out = new TreeMap<>(GalleryOps::compare);
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
        origin(out);
        lamps(out);
        skyline(out, seed);
        List<Parcel> parcels = new ArrayList<>();
        List<Frame> frames = new ArrayList<>();
        for (Parcel p : parcels()) {
            SplittableRandom rng = new SplittableRandom(seed * 1_000_033L + p.n());
            boolean gallery = rng.nextInt(100) < 40;
            if (gallery) {
                frames.addAll(gallery(out, p.bounds(), rng));
            }
            parcels.add(new Parcel(p.n(), p.bounds(), p.address(), gallery));
        }
        return new Plan(out, parcels, frames, streets());
    }

    private static BlockType surface(int dx, int dz, int x, int z, ParcelBounds plaza) {
        if (x >= plaza.minX() && x <= plaza.maxX() && z >= plaza.minZ() && z <= plaza.maxZ()) {
            return BlockType.PAVING;
        }
        int ax = Math.floorMod(dx, BLOCK + STREET);
        int az = Math.floorMod(dz, BLOCK + STREET);
        boolean streetX = ax < STREET || dx >= SIDE - STREET;
        boolean streetZ = az < STREET || dz >= SIDE - STREET;
        if (!streetX && !streetZ) {
            return BlockType.GRASS;
        }
        int across = streetX ? ax : az;
        if (dx >= SIDE - STREET) {
            across = dx - (SIDE - STREET);
        } else if (!streetX && dz >= SIDE - STREET) {
            across = dz - (SIDE - STREET);
        }
        return across == 0 || across == STREET - 1 ? BlockType.PAVING : BlockType.ROAD;
    }

    /** How far apart street lamps stand along a sidewalk. */
    static final int LAMP_SPACING = 8;
    /** A lamp post's height: the post, then the glowing head on top. */
    static final int LAMP_HEIGHT = 5;

    /**
     * Street lamps (ADR-038): a dark post with a glowing head on the outer edge of every sidewalk, every
     * {@link #LAMP_SPACING} cubes, never in a crossing. At night they light the streets; the realm hangs a real
     * light in the ones nearest the camera.
     */
    private static void lamps(Map<BlockCoordinate, BlockType> out) {
        for (int dx = 0; dx < SIDE; dx++) {
            for (int dz = 0; dz < SIDE; dz++) {
                int ax = Math.floorMod(dx, BLOCK + STREET);
                int az = Math.floorMod(dz, BLOCK + STREET);
                boolean streetX = ax < STREET;
                boolean streetZ = az < STREET;
                if (streetX == streetZ || dx >= SIDE - STREET || dz >= SIDE - STREET) {
                    continue;   // inside a block, in a crossing, or the outer ring road
                }
                int across = streetX ? ax : az;
                int along = streetX ? dz : dx;
                if ((across == 0 || across == STREET - 1) && Math.floorMod(along, LAMP_SPACING) == LAMP_SPACING / 2) {
                    int x = MIN_X + dx;
                    int z = MIN_Z + dz;
                    for (int y = 1; y < LAMP_HEIGHT; y++) {
                        out.put(new BlockCoordinate(x, GROUND_Y + y, z), BlockType.ROAD);
                    }
                    out.put(new BlockCoordinate(x, GROUND_Y + LAMP_HEIGHT, z), BlockType.LAMP);
                }
            }
        }
    }

    /** The skyline ring's distance outside the city, a tower's footprint, and the tallest tower. */
    static final int SKYLINE_GAP = 6;
    static final int TOWER = 8;
    static final int TOWER_MAX = 46;

    /**
     * A skyline (ADR-038): towers standing just outside the city, so the streets have a backdrop like Voxels'
     * Origin. They sit beyond the outer road, on no parcel, so nothing anyone can claim loses room. Walls of dark
     * stone with a grid of windows, some lit; a neon crown on top, pink or cyan. The seed varies heights and lights.
     */
    private static void skyline(Map<BlockCoordinate, BlockType> out, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5eedL);
        int lo = MIN_X - SKYLINE_GAP - TOWER;
        int hi = MIN_X + SIDE + SKYLINE_GAP;
        for (int t = lo; t <= hi; t += TOWER + 4) {
            tower(out, t, MIN_Z - SKYLINE_GAP - TOWER, rng);        // north row
            tower(out, t, MIN_Z + SIDE + SKYLINE_GAP, rng);         // south row
        }
        for (int t = MIN_Z; t < MIN_Z + SIDE; t += TOWER + 4) {
            tower(out, MIN_X - SKYLINE_GAP - TOWER, t, rng);        // west row
            tower(out, MIN_X + SIDE + SKYLINE_GAP, t, rng);         // east row
        }
    }

    private static void tower(Map<BlockCoordinate, BlockType> out, int x0, int z0, SplittableRandom rng) {
        if (rng.nextInt(100) < 25) {
            return;   // gaps in the skyline
        }
        int h = 18 + rng.nextInt(TOWER_MAX - 18);
        BlockType neon = rng.nextBoolean() ? BlockType.NEON_PINK : BlockType.NEON_CYAN;
        int lit = 25 + rng.nextInt(45);   // percent of windows lit
        for (int x = x0; x < x0 + TOWER; x++) {
            for (int z = z0; z < z0 + TOWER; z++) {
                boolean edge = x == x0 || x == x0 + TOWER - 1 || z == z0 || z == z0 + TOWER - 1;
                boolean corner = (x == x0 || x == x0 + TOWER - 1) && (z == z0 || z == z0 + TOWER - 1);
                for (int y = 1; y <= h; y++) {
                    if (!edge) {
                        continue;   // hollow: only the shell is drawn
                    }
                    boolean window = !corner && y % 3 != 0 && Math.floorMod(x + z, 2) == 0 && y < h - 1;
                    BlockType b = window ? (rng.nextInt(100) < lit ? BlockType.WINDOW_LIT : BlockType.GLASS) : BlockType.ROAD;
                    out.put(new BlockCoordinate(x, GROUND_Y + y, z), b);
                }
                out.put(new BlockCoordinate(x, GROUND_Y + h + 1, z), edge ? neon : BlockType.ROAD);
            }
        }
    }

    /** The Origin: a drone pad at the plaza's centre and a crystal spire beside it. */
    private static void origin(Map<BlockCoordinate, BlockType> out) {
        BlockCoordinate c = padBerth();
        for (int dx = -3; dx <= 2; dx++) {
            for (int dz = -3; dz <= 2; dz++) {
                boolean ring = dx == -3 || dx == 2 || dz == -3 || dz == 2;
                out.put(new BlockCoordinate(c.x() + dx, GROUND_Y, c.z() + dz), ring ? BlockType.HELIPAD : BlockType.PAVING);
            }
        }
        int sx = c.x() + 7;
        int sz = c.z() - 7;
        for (int y = 1; y <= 14; y++) {
            int r = y < 4 ? 1 : 0;
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    out.put(new BlockCoordinate(sx + dx, GROUND_Y + y, sz + dz), y < 4 ? BlockType.BRICK_WHITE : BlockType.CRYSTAL);
                }
            }
        }
    }

    /** A white gallery inside {@code b}, its glass front to the street; returns the frames on its inner walls. */
    private static List<Frame> gallery(Map<BlockCoordinate, BlockType> out, ParcelBounds b, SplittableRandom rng) {
        int x0 = b.minX() + 1;
        int x1 = b.maxX() - 1;
        int z0 = b.minZ() + 1;
        int z1 = b.maxZ() - 1;
        int h = Math.min(7, b.maxY() - 1);
        Facing front = front(b);
        for (int x = x0; x <= x1; x++) {
            for (int z = z0; z <= z1; z++) {
                out.put(new BlockCoordinate(x, GROUND_Y, z), BlockType.PAVING);
                boolean edge = x == x0 || x == x1 || z == z0 || z == z1;
                for (int y = 1; y <= h; y++) {
                    if (edge) {
                        boolean onFront = front == Facing.NORTH && z == z0 || front == Facing.SOUTH && z == z1
                                || front == Facing.WEST && x == x0 || front == Facing.EAST && x == x1;
                        BlockType t = onFront && y >= 2 && y < h ? BlockType.GLASS : BlockType.BRICK_WHITE;
                        out.put(new BlockCoordinate(x, GROUND_Y + y, z), t);
                    }
                }
                // the roof: glass inside, a rim of neon trim (ADR-038) so a gallery reads from down the street at night
                out.put(new BlockCoordinate(x, GROUND_Y + h + 1, z), edge ? BlockType.NEON_CYAN : BlockType.GLASS);
            }
        }
        // A door in the middle of the front, two wide and three high.
        int mx = (x0 + x1) / 2;
        int mz = (z0 + z1) / 2;
        for (int y = 1; y <= 3; y++) {
            for (int d = 0; d < 2; d++) {
                BlockCoordinate door = switch (front) {
                    case NORTH -> new BlockCoordinate(mx + d, y, z0);
                    case SOUTH -> new BlockCoordinate(mx + d, y, z1);
                    case WEST -> new BlockCoordinate(x0, y, mz + d);
                    case EAST -> new BlockCoordinate(x1, y, mz + d);
                };
                out.remove(door);
            }
        }
        // Art on each inner wall but the front: one frame, centred, three high, as wide as the wall allows.
        List<Frame> frames = new ArrayList<>();
        for (Facing wall : Facing.values()) {
            // A frame facing SOUTH hangs on the north wall (z0), and so on; the glass front holds none.
            if (wall == opposite(front)) {
                continue;
            }
            int len = wall.alongX() ? x1 - x0 - 1 : z1 - z0 - 1;
            int w = Math.min(len - 2, 3 + rng.nextInt(2));
            if (w < 2) {
                continue;
            }
            int startAlong = (wall.alongX() ? x0 + 1 : z0 + 1) + (len - w) / 2;
            int fy = GROUND_Y + 2;
            int fh = Math.min(3, h - 2);
            Frame f = switch (wall) {
                case SOUTH -> new Frame(startAlong, fy, z0, wall, w, fh, rng.nextInt(MAX_SEED));
                case NORTH -> new Frame(startAlong, fy, z1, wall, w, fh, rng.nextInt(MAX_SEED));
                case EAST -> new Frame(x0, fy, startAlong, wall, w, fh, rng.nextInt(MAX_SEED));
                case WEST -> new Frame(x1, fy, startAlong, wall, w, fh, rng.nextInt(MAX_SEED));
            };
            frames.add(f);
        }
        return frames;
    }

    static Facing opposite(Facing f) {
        return switch (f) {
            case NORTH -> Facing.SOUTH;
            case SOUTH -> Facing.NORTH;
            case EAST -> Facing.WEST;
            case WEST -> Facing.EAST;
        };
    }

    /**
     * True when {@code f} can hang in {@code world}: a 1..{@link #MAX_FRAME} by 1..{@link #MAX_FRAME} picture,
     * every wall cube behind it solid and opaque, and every cube in front of it open.
     */
    public static boolean fits(World world, Frame f) {
        if (f.w() < 1 || f.h() < 1 || f.w() > MAX_FRAME || f.h() > MAX_FRAME) {
            return false;
        }
        for (BlockCoordinate c : f.wall()) {
            BlockType wall = world.get(c);
            BlockType front = world.get(new BlockCoordinate(c.x() + f.facing().dx, c.y(), c.z() + f.facing().dz));
            if (!wall.solid() || wall.seeThrough() || !front.seeThrough()) {
                return false;
            }
        }
        return true;
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

    /** Lay the city out; false (and nothing placed) when anything is in the way. */
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
