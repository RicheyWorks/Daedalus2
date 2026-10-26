// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

/**
 * Fireline Warden (contest G27): a wind-driven wildfire runs at the homestead and a small crew fights it on a
 * {@link BattlefieldEcology} field, using the battlefield fire rules (ADR-061) for the spread.
 *
 * <p>Each tick the crew has a few actions, all within {@code reach} cells of the homestead:
 * <ul>
 *   <li>{@link #cut} clears a cell to bare ground: a permanent break, but the growth is lost.</li>
 *   <li>{@link #wet} soaks a cell from the water tank: it cannot burn for {@code wetTicks} ticks, then dries out. The
 *       growth survives.</li>
 *   <li>{@link #douse} puts out a burning cell from the tank.</li>
 * </ul>
 * The tank refills slowly. Then {@link #tick()} runs one tick of fire. The homestead is LOST the moment any of its
 * cells burns. With the homestead safe, the outcome is HELD when enough of the starting growth survives, otherwise
 * SAVED. Deterministic: the fire uses the field's seeded draws, and the crew's moves are the only other input.
 */
public final class FirelineWarden {

    public enum Outcome { BURNING, HELD, SAVED, LOST }

    /** A rectangle of cells, inclusive. */
    public record Plot(int i0, int j0, int i1, int j1) {
        public Plot {
            if (i0 > i1 || j0 > j1) {
                throw new IllegalArgumentException("plot corners out of order");
            }
        }

        public boolean contains(int i, int j) { return i >= i0 && i <= i1 && j >= j0 && j <= j1; }
    }

    /**
     * Tuning.
     *
     * @param crew        crew actions per tick
     * @param reach       the crew works within this many cells of the homestead (Chebyshev)
     * @param tank        water tank capacity (one unit per wet or douse)
     * @param refill      water back per tick (water cart from the spring)
     * @param wetTicks    ticks a wetted cell stays fireproof
     * @param heldTarget  HELD when at least this share of the starting growth survives
     * @param maxTicks    the fire is called out after this many ticks
     */
    public record Settings(int crew, int reach, int tank, int refill, int wetTicks, double heldTarget, int maxTicks) {
        public static final Settings DEFAULT = new Settings(3, 6, 24, 1, 8, 0.6, 400);

        public Settings {
            if (crew < 1 || reach < 0 || tank < 0 || refill < 0 || wetTicks < 1 || !(heldTarget > 0 && heldTarget <= 1)
                    || maxTicks < 1) {
                throw new IllegalArgumentException("bad FirelineWarden settings");
            }
        }
    }

    /** One tick: cells newly lit, cells still burning, water left, nearest flame to the homestead (cells). */
    public record Tick(long index, int lit, int burning, int water, int frontDistance) {}

    /** End-of-fire summary. {@code saved} is the share of the starting growth neither burnt nor cut. */
    public record Report(Outcome outcome, long ticks, double saved, int burnt, int cut, int wetted, int doused,
            int waterLeft) {}

    private final BattlefieldEcology field;
    private final Settings s;
    private final Plot home;
    private final int w;
    private final int h;
    private final boolean[] grown;
    private final boolean[] cutMask;
    private final int[] wetLeft;
    private final int growth;
    private int actionsLeft;
    private int water;
    private long ticks;
    private int cuts;
    private int wets;
    private int douses;
    private boolean lost;

    private FirelineWarden(BattlefieldEcology field, Plot home, Settings s) {
        this.field = field;
        this.s = s;
        this.home = home;
        this.w = field.width();
        this.h = field.height();
        if (home.i0() < 0 || home.j0() < 0 || home.i1() >= w || home.j1() >= h) {
            throw new IllegalArgumentException("homestead plot outside the field");
        }
        this.grown = new boolean[w * h];
        this.cutMask = new boolean[w * h];
        this.wetLeft = new int[w * h];
        int g = 0;
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                if (field.vegetation(i, j).flammability() > 0) {
                    grown[j * w + i] = true;
                    g++;
                }
            }
        }
        this.growth = g;
        this.actionsLeft = s.crew();
        this.water = s.tank();
    }

    /** Takes command of the fire on this field, with the homestead on the given plot. */
    public static FirelineWarden command(BattlefieldEcology field, Plot homestead, Settings settings) {
        if (field == null || homestead == null || settings == null) {
            throw new IllegalArgumentException("field, homestead and settings are required");
        }
        return new FirelineWarden(field, homestead, settings);
    }

    /** Lightning (or a stray shell): lights everything flammable within the radius. Returns the cells lit. */
    public int ignite(double x, double y, double radiusCm) {
        return field.apply(BattlefieldEcology.EventKind.IGNITE, x, y, radiusCm);
    }

    public FirelineWarden wind(double x, double y) {
        field.wind(x, y);
        return this;
    }

    // ---- crew actions -------------------------------------------------------------------------------------------

    /** Cuts a break: the cell goes bare for good. Refused on a burning cell, out of reach or with no crew actions left. */
    public boolean cut(double x, double y) {
        int i = field.cellI(x);
        int j = field.cellJ(y);
        if (actionsLeft == 0 || !inReach(i, j) || field.burning(i, j) > 0) {
            return false;
        }
        actionsLeft--;
        if (field.vegetation(i, j) != Vegetation.BARE && field.vegetation(i, j) != Vegetation.WETLAND) {
            field.set(i, j, Vegetation.BARE);
            cutMask[j * w + i] = true;
            cuts++;
        }
        return true;
    }

    /** Wets a cell so it cannot burn for {@code wetTicks}. Refused on a burning cell, out of reach, with no water or no crew. */
    public boolean wet(double x, double y) {
        int i = field.cellI(x);
        int j = field.cellJ(y);
        if (actionsLeft == 0 || water == 0 || !inReach(i, j) || field.burning(i, j) > 0) {
            return false;
        }
        actionsLeft--;
        water--;
        wetLeft[j * w + i] = s.wetTicks();
        wets++;
        return true;
    }

    /** Puts out a burning cell. Refused when the cell is not burning, out of reach, or with no water or no crew. */
    public boolean douse(double x, double y) {
        int i = field.cellI(x);
        int j = field.cellJ(y);
        if (actionsLeft == 0 || water == 0 || !inReach(i, j) || field.burning(i, j) == 0) {
            return false;
        }
        actionsLeft--;
        water--;
        field.apply(BattlefieldEcology.EventKind.DOUSE, field.centreX(i), field.centreY(j), 0);
        douses++;
        return true;
    }

    // ---- time ---------------------------------------------------------------------------------------------------

    /** One tick of fire. Wet cells that caught are put out first, then the fire spreads, then the crew rests. */
    public Tick tick() {
        if (lost) {
            throw new IllegalStateException("the homestead is lost");
        }
        quenchWet();
        int lit = field.tick();
        ticks++;
        quenchWet();
        for (int k = 0; k < wetLeft.length; k++) {
            if (wetLeft[k] > 0) {
                wetLeft[k]--;
            }
        }
        actionsLeft = s.crew();
        water = Math.min(s.tank(), water + s.refill());
        int burning = 0;
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                if (field.burning(i, j) > 0) {
                    burning++;
                    if (home.contains(i, j)) {
                        lost = true;
                    }
                }
            }
        }
        return new Tick(ticks, lit, burning, water, frontDistance());
    }

    /** Runs the fire out: the plan moves the crew before every tick, until the fire is out, lost or called. */
    public Report play(Plan plan) {
        while (outcome() == Outcome.BURNING && ticks < s.maxTicks()) {
            if (plan != null) {
                plan.before(this, ticks);
            }
            tick();
        }
        return report();
    }

    /** The crew's moves before a tick. */
    @FunctionalInterface
    public interface Plan {
        void before(FirelineWarden warden, long tick);
    }

    // ---- queries ------------------------------------------------------------------------------------------------

    public int actionsLeft() { return actionsLeft; }
    public int water() { return water; }
    public long ticks() { return ticks; }
    public boolean wet(int i, int j) { return wetLeft[index(i, j)] > 0; }
    public boolean cutAt(int i, int j) { return cutMask[index(i, j)]; }

    /** Cells burning now. */
    public int burning() {
        int n = 0;
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                n += field.burning(i, j) > 0 ? 1 : 0;
            }
        }
        return n;
    }

    /** True when the crew can work the cell: within {@code reach} cells of the homestead. */
    public boolean inReach(int i, int j) {
        return distanceToHome(i, j) <= s.reach();
    }

    /** Chebyshev distance in cells from the nearest flame to the homestead plot; -1 when nothing burns. */
    public int frontDistance() {
        int best = -1;
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                if (field.burning(i, j) > 0) {
                    int d = distanceToHome(i, j);
                    best = best < 0 ? d : Math.min(best, d);
                }
            }
        }
        return best;
    }

    public Outcome outcome() {
        if (lost) {
            return Outcome.LOST;
        }
        if (burning() > 0) {
            return Outcome.BURNING;
        }
        return saved() >= s.heldTarget() ? Outcome.HELD : Outcome.SAVED;
    }

    /** Share of the starting growth that is neither burnt nor cut. */
    public double saved() {
        return growth == 0 ? 1 : (double) (growth - burnt() - cuts) / growth;
    }

    /** Starting growth burnt to bare ground (cut cells not counted). */
    public int burnt() {
        int n = 0;
        for (int k = 0; k < grown.length; k++) {
            if (grown[k] && !cutMask[k] && field.vegetation(k % w, k / w) == Vegetation.BARE) {
                n++;
            }
        }
        return n;
    }

    public Report report() {
        return new Report(outcome(), ticks, saved(), burnt(), cuts, wets, douses, water);
    }

    // ---- internals ----------------------------------------------------------------------------------------------

    private int distanceToHome(int i, int j) {
        int di = i < home.i0() ? home.i0() - i : Math.max(0, i - home.i1());
        int dj = j < home.j0() ? home.j0() - j : Math.max(0, j - home.j1());
        return Math.max(di, dj);
    }

    private void quenchWet() {
        for (int k = 0; k < wetLeft.length; k++) {
            int i = k % w;
            int j = k / w;
            if (wetLeft[k] > 0 && field.burning(i, j) > 0) {
                field.apply(BattlefieldEcology.EventKind.DOUSE, field.centreX(i), field.centreY(j), 0);
            }
        }
    }

    private int index(int i, int j) {
        if (i < 0 || j < 0 || i >= w || j >= h) {
            throw new IndexOutOfBoundsException("cell " + i + "," + j + " outside " + w + "x" + h);
        }
        return j * w + i;
    }
}
