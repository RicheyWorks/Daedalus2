// SPDX-License-Identifier: MIT

package com.daedalus.world.bricks;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.BlockType;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * BRK01 Missing Piece Collector (contest gap G16): the Unmaker has scattered the airfield's machines across
 * the Bricks baseplate. The player gathers the pieces, PocketBot highlights candidates, and each slot of a
 * machine is fitted with a piece the player chooses. Restoring the {@link Machine#PLANE} opens the airfield,
 * so the Bricks world reaches its sky gate by air; the {@link Machine#HOVER_CART} gives ground travel.
 *
 * <p><b>Forge tie-in.</b> Every piece carries wear (0..100). A fit is graded like a temper, in integer
 * per-mille: {@code quality = 1000 - 10 * wear}, giving PERFECT, SNUG, LOOSE or REJECT (cracked or the
 * wrong shape). A worn piece can be re-baked once at the Kiln (a limited number of charges per session),
 * which takes {@link #KILN_RESTORE} wear off. A machine is only as good as its weakest fit.
 *
 * <p><b>Host-authoritative and fair.</b> {@link Session} owns the state: a piece is collected once, from
 * within {@link #REACH}, and consumed by exactly one slot; a rejected fit consumes nothing. The scatter is
 * pure data: it never edits the world, and every piece lies on a free, unprotected baseplate cell (see
 * {@link BricksOps#protects}), so no player build, deed or the obby is touched. Every slot always has a
 * genuine piece that fits, so every seed is solvable.
 *
 * <p>Deterministic: one {@code SplittableRandom(seed)} drives the scatter.
 */
public final class AssemblyRepair {

    /** Horizontal reach, in cubes, for picking a piece up. */
    public static final double REACH = 3.0;
    /** Kiln charges per session. */
    public static final int KILN_CHARGES = 3;
    /** Wear one Kiln re-bake removes. */
    public static final int KILN_RESTORE = 30;
    /** Highest wear a genuine piece is scattered with: always at least LOOSE. */
    public static final int GENUINE_MAX_WEAR = 60;
    /** Spares (same shape as a slot, often badly worn) and decoys (shapes no slot takes). */
    public static final int DECOYS = 6;
    /** Shapes no machine uses, so a decoy can never fit. */
    static final List<String> DECOY_SHAPES = List.of("1x1", "3x3", "2x5", "1x3", "4x4", "2x7");

    /** A machine the Unmaker took apart. */
    public enum Machine {
        PLANE("Brick Plane", true),
        HOVER_CART("Hover Cart", false);

        private final String title;
        private final boolean opensSkyGate;

        Machine(String title, boolean opensSkyGate) {
            this.title = title;
            this.opensSkyGate = opensSkyGate;
        }

        public String title() {
            return title;
        }

        /** True when restoring this machine opens the airfield route to the sky gate. */
        public boolean opensSkyGate() {
            return opensSkyGate;
        }

        public List<Slot> slots() {
            List<Slot> out = new ArrayList<>();
            for (Slot s : Slot.values()) {
                if (s.machine == this) {
                    out.add(s);
                }
            }
            return out;
        }
    }

    /** One place on a machine that takes a piece of one stud shape. */
    public enum Slot {
        FUSELAGE(Machine.PLANE, "2x8"),
        LEFT_WING(Machine.PLANE, "2x6"),
        RIGHT_WING(Machine.PLANE, "2x6"),
        PROPELLER(Machine.PLANE, "1x4"),
        TAIL(Machine.PLANE, "2x3"),
        WHEELS(Machine.PLANE, "1x2"),
        DECK(Machine.HOVER_CART, "4x6"),
        FAN(Machine.HOVER_CART, "2x2"),
        RAIL(Machine.HOVER_CART, "1x6"),
        SEAT(Machine.HOVER_CART, "2x2");

        private final Machine machine;
        private final String shape;

        Slot(Machine machine, String shape) {
            this.machine = machine;
            this.shape = shape;
        }

        public Machine machine() {
            return machine;
        }

        public String shape() {
            return shape;
        }
    }

    /** How well a piece seats in a slot. */
    public enum Grade {
        PERFECT(850), SNUG(600), LOOSE(300), REJECT(0);

        private final int minQuality;

        Grade(int minQuality) {
            this.minQuality = minQuality;
        }

        public int minQuality() {
            return minQuality;
        }

        public boolean seats() {
            return this != REJECT;
        }

        static Grade of(int quality) {
            for (Grade g : values()) {
                if (quality >= g.minQuality && g != REJECT) {
                    return g;
                }
            }
            return REJECT;
        }
    }

    /** One scattered piece: its id, stud shape, colour, wear and the cell it lies on. */
    public record Piece(int id, String shape, BlockType color, int wear, BlockCoordinate at) {

        public Piece {
            if (wear < 0 || wear > 100) {
                throw new IllegalArgumentException("wear out of range: " + wear);
            }
        }

        /** Fit quality in per-mille: 1000 for a fresh piece, 0 for a fully worn one. */
        public int quality() {
            return 1000 - 10 * wear;
        }
    }

    /** The scattered airfield of one seed. */
    public record Scatter(long seed, List<Piece> pieces) {

        public Scatter {
            pieces = List.copyOf(pieces);
        }

        public Piece piece(int id) {
            for (Piece p : pieces) {
                if (p.id() == id) {
                    return p;
                }
            }
            return null;
        }
    }

    /** The outcome of one session action. */
    public enum Outcome {
        OK, UNKNOWN_PIECE, TOO_FAR, ALREADY_COLLECTED, NOT_COLLECTED, ALREADY_USED, SLOT_FILLED, REJECTED,
        NO_KILN_CHARGES, ALREADY_REBAKED
    }

    /** A fitted slot: which piece and how well. */
    public record Fit(Slot slot, int pieceId, int quality, Grade grade) {
    }

    /** The objective-gate receipt for one machine. */
    public record Receipt(Machine machine, boolean restored, Grade weakest, int meanQuality,
                          List<Integer> piecesUsed, int rejects, int kilnUses, boolean skyGateOpen) {

        public Receipt {
            piecesUsed = List.copyOf(piecesUsed);
        }
    }

    private AssemblyRepair() {
    }

    /** Grade a piece against a slot: REJECT for the wrong shape or a cracked piece. */
    public static Grade grade(Piece piece, Slot slot) {
        if (!piece.shape().equals(slot.shape())) {
            return Grade.REJECT;
        }
        return Grade.of(piece.quality());
    }

    /** The airfield the Unmaker left for {@code seed}: one genuine piece per slot, spares and decoys. */
    public static Scatter scatter(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xB4C01L);
        BlockType[] colors = {BlockType.BRICK_RED, BlockType.BRICK_BLUE, BlockType.BRICK_GREEN,
            BlockType.BRICK_YELLOW, BlockType.BRICK_WHITE};
        List<String> shapes = new ArrayList<>();
        List<Integer> wears = new ArrayList<>();
        for (Slot s : Slot.values()) {
            shapes.add(s.shape());
            wears.add(rng.nextInt(GENUINE_MAX_WEAR + 1));
            if (rng.nextInt(2) == 0) {                      // a spare: same shape, usually worse
                shapes.add(s.shape());
                wears.add(40 + rng.nextInt(61));
            }
        }
        for (int i = 0; i < DECOYS; i++) {
            shapes.add(DECOY_SHAPES.get(rng.nextInt(DECOY_SHAPES.size())));
            wears.add(rng.nextInt(101));
        }
        List<Integer> order = new ArrayList<>();
        for (int i = 0; i < shapes.size(); i++) {
            order.add(i);
        }
        Collections.shuffle(order, new Random(rng.nextLong()));
        Set<BlockCoordinate> used = new HashSet<>();
        List<Piece> out = new ArrayList<>();
        for (int id = 0; id < order.size(); id++) {
            int k = order.get(id);
            out.add(new Piece(id, shapes.get(k), colors[rng.nextInt(colors.length)], wears.get(k), freeCell(rng, used)));
        }
        return new Scatter(seed, out);
    }

    private static BlockCoordinate freeCell(SplittableRandom rng, Set<BlockCoordinate> used) {
        while (true) {
            BlockCoordinate at = new BlockCoordinate(BricksOps.MIN_X + rng.nextInt(BricksOps.SIDE),
                    BricksOps.TOP_Y + 1, BricksOps.MIN_Z + rng.nextInt(BricksOps.SIDE));
            if (!BricksOps.protects(at) && used.add(at)) {
                return at;
            }
        }
    }

    /** Horizontal distance between two cells. */
    static double distance(BlockCoordinate a, BlockCoordinate b) {
        int dx = a.x() - b.x();
        int dz = a.z() - b.z();
        return Math.sqrt((double) dx * dx + (double) dz * dz);
    }

    /** One player's repair run over a scatter; the host owns this state. */
    public static final class Session {

        private final Scatter scatter;
        private final Set<Integer> bag = new HashSet<>();
        private final Set<Integer> used = new HashSet<>();
        private final Set<Integer> rebaked = new HashSet<>();
        private final Map<Integer, Integer> wear = new LinkedHashMap<>();
        private final Map<Slot, Fit> fits = new EnumMap<>(Slot.class);
        private final Map<Machine, Integer> rejects = new EnumMap<>(Machine.class);
        private int kilnUses;

        public Session(Scatter scatter) {
            this.scatter = scatter;
            for (Piece p : scatter.pieces()) {
                wear.put(p.id(), p.wear());
            }
        }

        /** Pick up a piece lying within reach of {@code avatar}. */
        public Outcome collect(int pieceId, BlockCoordinate avatar) {
            Piece p = scatter.piece(pieceId);
            if (p == null) {
                return Outcome.UNKNOWN_PIECE;
            }
            if (bag.contains(pieceId) || used.contains(pieceId)) {
                return Outcome.ALREADY_COLLECTED;
            }
            if (distance(p.at(), avatar) > REACH || Math.abs(p.at().y() - avatar.y()) > 2) {
                return Outcome.TOO_FAR;
            }
            bag.add(pieceId);
            return Outcome.OK;
        }

        /** Re-bake a collected, unfitted piece at the Kiln, once per piece. */
        public Outcome rebake(int pieceId) {
            if (scatter.piece(pieceId) == null) {
                return Outcome.UNKNOWN_PIECE;
            }
            if (used.contains(pieceId)) {
                return Outcome.ALREADY_USED;
            }
            if (!bag.contains(pieceId)) {
                return Outcome.NOT_COLLECTED;
            }
            if (rebaked.contains(pieceId)) {
                return Outcome.ALREADY_REBAKED;
            }
            if (kilnUses >= KILN_CHARGES) {
                return Outcome.NO_KILN_CHARGES;
            }
            kilnUses++;
            rebaked.add(pieceId);
            wear.put(pieceId, Math.max(0, wear.get(pieceId) - KILN_RESTORE));
            return Outcome.OK;
        }

        /** The piece as it is now (wear after any Kiln re-bake). */
        public Piece current(int pieceId) {
            Piece p = scatter.piece(pieceId);
            return p == null ? null : new Piece(p.id(), p.shape(), p.color(), wear.get(pieceId), p.at());
        }

        /** Fit a collected piece into a slot; a REJECT leaves the piece in the bag. */
        public Outcome fit(Slot slot, int pieceId) {
            if (scatter.piece(pieceId) == null) {
                return Outcome.UNKNOWN_PIECE;
            }
            if (used.contains(pieceId)) {
                return Outcome.ALREADY_USED;
            }
            if (!bag.contains(pieceId)) {
                return Outcome.NOT_COLLECTED;
            }
            if (fits.containsKey(slot)) {
                return Outcome.SLOT_FILLED;
            }
            Piece p = current(pieceId);
            Grade g = grade(p, slot);
            if (!g.seats()) {
                rejects.merge(slot.machine(), 1, Integer::sum);
                return Outcome.REJECTED;
            }
            bag.remove(pieceId);
            used.add(pieceId);
            fits.put(slot, new Fit(slot, pieceId, p.quality(), g));
            return Outcome.OK;
        }

        /** PocketBot: uncollected pieces of the slot's shape, nearest first (it cannot see wear). */
        public List<Piece> hints(Slot slot, BlockCoordinate from) {
            List<Piece> out = new ArrayList<>();
            for (Piece p : scatter.pieces()) {
                if (p.shape().equals(slot.shape()) && !bag.contains(p.id()) && !used.contains(p.id())) {
                    out.add(p);
                }
            }
            out.sort(Comparator.comparingDouble((Piece p) -> distance(p.at(), from)).thenComparingInt(Piece::id));
            return out;
        }

        /** Pieces in the bag, by id. */
        public List<Integer> bag() {
            List<Integer> out = new ArrayList<>(bag);
            Collections.sort(out);
            return out;
        }

        public Fit fitted(Slot slot) {
            return fits.get(slot);
        }

        public int kilnUses() {
            return kilnUses;
        }

        /** The objective gate for {@code machine}: restored only when every slot seats a piece. */
        public Receipt receipt(Machine machine) {
            List<Integer> pieces = new ArrayList<>();
            Grade weakest = Grade.PERFECT;
            int sum = 0;
            boolean restored = true;
            for (Slot s : machine.slots()) {
                Fit f = fits.get(s);
                if (f == null) {
                    restored = false;
                    continue;
                }
                pieces.add(f.pieceId());
                sum += f.quality();
                if (f.grade().ordinal() > weakest.ordinal()) {
                    weakest = f.grade();
                }
            }
            int mean = pieces.isEmpty() ? 0 : sum / pieces.size();
            return new Receipt(machine, restored, restored ? weakest : Grade.REJECT, mean, pieces,
                    rejects.getOrDefault(machine, 0), kilnUses, restored && machine.opensSkyGate());
        }

        /** True once the airfield is restored: some restored machine opens the sky gate route. */
        public boolean airfieldOpen() {
            for (Machine m : Machine.values()) {
                if (receipt(m).skyGateOpen()) {
                    return true;
                }
            }
            return false;
        }
    }
}
