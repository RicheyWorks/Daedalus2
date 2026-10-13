// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.Arrays;

/**
 * The environment that reacts to the fight (ADR-061): a grid of vegetation cells over a battlefield, in Unreal
 * centimetres. Combat events ignite, blast or douse cells; {@link #tick()} spreads fire for one combat tick;
 * {@link #grow(double)} advances succession between encounters. Cover and concealment queries feed the Adaptive
 * Combat Director (DTO 1, ADR-060) without it knowing anything about plants.
 *
 * <p>Deterministic: every random draw is a pure hash of (seed, tick, cell), so the result never depends on iteration
 * order or thread count, and a replay from the same seed and events is bit-identical.
 */
public final class BattlefieldEcology {

    public enum EventKind { IGNITE, BLAST, DOUSE }

    private final int width;
    private final int height;
    private final double cellCm;
    private final double originX;
    private final double originY;
    private final long seed;
    private final Vegetation[] veg;
    private final double[] age;      // years in the current stage
    private final int[] burning;     // ticks of fire left, 0 = not burning
    private long tick;
    private double windX;
    private double windY;

    public BattlefieldEcology(int width, int height, double cellCm, double originX, double originY, long seed) {
        if (width < 1 || height < 1 || width > 4096 || height > 4096) {
            throw new IllegalArgumentException("grid must be 1..4096 cells per side");
        }
        if (!(cellCm > 0)) {
            throw new IllegalArgumentException("cellCm must be > 0");
        }
        this.width = width;
        this.height = height;
        this.cellCm = cellCm;
        this.originX = originX;
        this.originY = originY;
        this.seed = seed;
        this.veg = new Vegetation[width * height];
        this.age = new double[width * height];
        this.burning = new int[width * height];
        Arrays.fill(veg, Vegetation.MEADOW);
    }

    // ---- setup -------------------------------------------------------------------------------------------------

    public BattlefieldEcology set(int i, int j, Vegetation v) {
        int k = index(i, j);
        veg[k] = v;
        age[k] = 0;
        burning[k] = 0;
        return this;
    }

    /** Wind pushes fire: a burning cell lights downwind neighbours more readily (each component clamped to -1..1). */
    public BattlefieldEcology wind(double x, double y) {
        this.windX = Math.max(-1, Math.min(1, x));
        this.windY = Math.max(-1, Math.min(1, y));
        return this;
    }

    // ---- combat events -----------------------------------------------------------------------------------------

    /**
     * Applies a combat event at a world point. IGNITE lights every flammable cell within radius; BLAST strips cells
     * to BARE (craters, felled trees) and lights the rim; DOUSE puts fires out. Returns the number of cells changed.
     */
    public int apply(EventKind kind, double x, double y, double radiusCm) {
        if (!(radiusCm >= 0)) {
            throw new IllegalArgumentException("radius must be >= 0");
        }
        int changed = 0;
        int r = (int) Math.ceil(radiusCm / cellCm) + 1;
        int ci = cellI(x);
        int cj = cellJ(y);
        for (int j = Math.max(0, cj - r); j <= Math.min(height - 1, cj + r); j++) {
            for (int i = Math.max(0, ci - r); i <= Math.min(width - 1, ci + r); i++) {
                double d = (i == ci && j == cj) ? 0 : Math.hypot(centreX(i) - x, centreY(j) - y);
                int k = j * width + i;
                switch (kind) {
                    case IGNITE -> {
                        if (d <= radiusCm && veg[k].flammability() > 0 && burning[k] == 0) {
                            burning[k] = veg[k].burnTicks();
                            changed++;
                        }
                    }
                    case BLAST -> {
                        if (d <= radiusCm && veg[k] != Vegetation.BARE && veg[k] != Vegetation.WETLAND) {
                            veg[k] = Vegetation.BARE;
                            age[k] = 0;
                            burning[k] = 0;
                            changed++;
                        } else if (d <= radiusCm + cellCm && veg[k].flammability() > 0 && burning[k] == 0) {
                            burning[k] = veg[k].burnTicks();
                            changed++;
                        }
                    }
                    case DOUSE -> {
                        if (d <= radiusCm && burning[k] > 0) {
                            burning[k] = 0;
                            changed++;
                        }
                    }
                    default -> throw new IllegalStateException("unhandled event " + kind);
                }
            }
        }
        return changed;
    }

    // ---- time --------------------------------------------------------------------------------------------------

    /** One combat tick of fire: burning cells may light their 4 neighbours, then burn down; burnt-out cells go BARE. */
    public int tick() {
        int[] next = burning.clone();
        int lit = 0;
        for (int j = 0; j < height; j++) {
            for (int i = 0; i < width; i++) {
                int k = j * width + i;
                if (burning[k] > 0) {
                    continue;
                }
                double f = veg[k].flammability();
                if (f <= 0) {
                    continue;
                }
                double p = 0;
                p = Math.max(p, spread(i - 1, j, f, windX));
                p = Math.max(p, spread(i + 1, j, f, -windX));
                p = Math.max(p, spread(i, j - 1, f, windY));
                p = Math.max(p, spread(i, j + 1, f, -windY));
                if (p > 0 && draw(k) < p) {
                    next[k] = veg[k].burnTicks();
                    lit++;
                }
            }
        }
        for (int k = 0; k < next.length; k++) {
            if (burning[k] > 0) {
                next[k] = burning[k] - 1;
                if (next[k] == 0) {
                    veg[k] = Vegetation.BARE;
                    age[k] = 0;
                }
            }
        }
        System.arraycopy(next, 0, burning, 0, next.length);
        tick++;
        return lit;
    }

    private double spread(int i, int j, double f, double windToward) {
        if (i < 0 || j < 0 || i >= width || j >= height || burning[j * width + i] == 0) {
            return 0;
        }
        // windToward > 0 means the wind blows from the burning neighbour toward this cell
        // spread the total chance f over the target's burn time so slow-burning wood is not lit more often
        double total = Math.min(1, f * (1 + 0.8 * windToward));
        int ticks = Math.max(1, veg[j * width + i].burnTicks());
        return 1 - Math.pow(1 - total, 1.0 / ticks);
    }

    /** Quiet years between encounters: every unburnt cell ages and climbs the succession ladder. */
    public void grow(double years) {
        if (!(years >= 0)) {
            throw new IllegalArgumentException("years must be >= 0");
        }
        for (int k = 0; k < veg.length; k++) {
            if (burning[k] > 0) {
                continue;
            }
            double left = years;
            while (left > 0) {
                double need = veg[k].yearsToNext() - age[k];
                if (veg[k].yearsToNext() <= 0) {
                    age[k] += left;
                    break;
                }
                if (left < need) {
                    age[k] += left;
                    break;
                }
                left -= need;
                veg[k] = veg[k].next();
                age[k] = 0;
            }
        }
    }

    // ---- queries for the combat director -----------------------------------------------------------------------

    public Vegetation at(double x, double y) { return veg[index(cellI(x), cellJ(y))]; }
    public double coverAt(double x, double y) { return at(x, y).cover(); }
    public boolean burningAt(double x, double y) { return burning[index(cellI(x), cellJ(y))] > 0; }

    /**
     * How hidden a target at (tx,ty) is from an observer at (ox,oy): 1 minus the product of (1 - concealment) of every
     * cell the sight line crosses, excluding the observer's own cell. Burning cells add smoke (0.5).
     */
    public double concealmentBetween(double ox, double oy, double tx, double ty) {
        double len = Math.hypot(tx - ox, ty - oy);
        int steps = Math.max(1, (int) Math.ceil(len / (cellCm / 2)));
        int lastK = index(cellI(ox), cellJ(oy));
        double seen = 1;
        for (int s = 1; s <= steps; s++) {
            double x = ox + (tx - ox) * s / steps;
            double y = oy + (ty - oy) * s / steps;
            int k = index(cellI(x), cellJ(y));
            if (k == lastK) {
                continue;
            }
            lastK = k;
            double c = burning[k] > 0 ? Math.max(0.5, veg[k].concealment()) : veg[k].concealment();
            seen *= 1 - c * 0.5;   // each cell hides half its concealment; a full canopy strip still lets glimpses through
        }
        return 1 - seen;
    }

    /**
     * Best cover cell for a unit at (ux,uy) within radiusCm against a threat at (thx,thy): maximises cover plus
     * concealment from the threat, avoids fire, and prefers nearer cells on ties. Returns {x, y, score} in cm.
     */
    public double[] bestCover(double ux, double uy, double thx, double thy, double radiusCm) {
        int r = (int) Math.ceil(radiusCm / cellCm);
        int ci = cellI(ux);
        int cj = cellJ(uy);
        double best = -1;
        double bx = centreX(ci);
        double by = centreY(cj);
        for (int j = Math.max(0, cj - r); j <= Math.min(height - 1, cj + r); j++) {
            for (int i = Math.max(0, ci - r); i <= Math.min(width - 1, ci + r); i++) {
                double x = centreX(i);
                double y = centreY(j);
                double d = Math.hypot(x - ux, y - uy);
                if (d > radiusCm) {
                    continue;
                }
                int k = j * width + i;
                if (burning[k] > 0) {
                    continue;
                }
                double score = veg[k].cover() + 0.5 * concealmentBetween(thx, thy, x, y) - 1e-6 * d;
                if (score > best) {
                    best = score;
                    bx = x;
                    by = y;
                }
            }
        }
        return new double[] {bx, by, Math.max(0, best)};
    }

    /** Count of cells per vegetation state, in enum order, plus burning cells last. */
    public int[] census() {
        int[] c = new int[Vegetation.values().length + 1];
        for (int k = 0; k < veg.length; k++) {
            c[veg[k].ordinal()]++;
            if (burning[k] > 0) {
                c[c.length - 1]++;
            }
        }
        return c;
    }

    // ---- geometry and accessors --------------------------------------------------------------------------------

    public int width() { return width; }
    public int height() { return height; }
    public double cellCm() { return cellCm; }
    public double originX() { return originX; }
    public double originY() { return originY; }
    public long seed() { return seed; }
    public long tickCount() { return tick; }
    public Vegetation vegetation(int i, int j) { return veg[index(i, j)]; }
    public int burning(int i, int j) { return burning[index(i, j)]; }

    void restore(long tick, int i, int j, Vegetation v, int burn) {
        this.tick = tick;
        int k = index(i, j);
        veg[k] = v;
        burning[k] = burn;
    }

    public int cellI(double x) { return clamp((int) Math.floor((x - originX) / cellCm), width); }
    public int cellJ(double y) { return clamp((int) Math.floor((y - originY) / cellCm), height); }
    public double centreX(int i) { return originX + (i + 0.5) * cellCm; }
    public double centreY(int j) { return originY + (j + 0.5) * cellCm; }

    private static int clamp(int v, int n) { return Math.max(0, Math.min(n - 1, v)); }

    private int index(int i, int j) {
        if (i < 0 || j < 0 || i >= width || j >= height) {
            throw new IndexOutOfBoundsException("cell " + i + "," + j + " outside " + width + "x" + height);
        }
        return j * width + i;
    }

    /** SplitMix64 of (seed, tick, cell) mapped to [0,1): order-independent, reproducible. */
    private double draw(int k) {
        long z = seed ^ (tick * 0x9E3779B97F4A7C15L) ^ ((long) k * 0xC2B2AE3D27D4EB4FL);
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z ^= z >>> 31;
        return (z >>> 11) * 0x1.0p-53;
    }
}
