// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Ashfall Regrowth (contest G20): a Daedalus island fragment scorched by the impact that shattered the planet regrows
 * by succession, and the player steers the recovery against new fire.
 *
 * <p>The fragment is a {@link BattlefieldEcology} field; its WETLAND cells at start are water (springs, pools, shore)
 * and everything else is scorched to ash. Each {@link #season()} the land grows up the bands
 * ASH, MEADOW, BRAMBLE, PINE, OAK (WILLOW instead of bramble on cells beside water), then a dry-season lightning
 * strike may land with a chance that grows with the fuel on the fragment, and the fire spreads with the
 * battlefield fire rules ({@link BattlefieldEcology#tick()}).
 *
 * <p>The player has three tools:
 * <ul>
 *   <li>{@link #seedCache} opens an ark seed cache: ash within the cache radius turns to meadow at once. Ash only
 *       greens from seed rain, so a cell with no living cell within {@code seedReach} stays sterile forever.</li>
 *   <li>{@link #water} carries water from a source (within {@code carryCells} of water) to a patch for one season: it
 *       grows faster and fire cannot take it.</li>
 *   <li>{@link #graze} sets a livestock herd on a patch for good: the grazers crop bramble back to meadow and hold
 *       it there, and the cropped turf does not carry fire. A grazed patch never grows into forest.</li>
 * </ul>
 * Seeded and deterministic: the same field, settings, seed and actions give the same run.
 */
public final class AshfallRegrowth {

    /** Recovery bands as the player sees them, each drawn with a battlefield vegetation state. */
    public enum Band {
        ASH(Vegetation.BARE), MEADOW(Vegetation.MEADOW), BRAMBLE(Vegetation.SCRUB), PINE(Vegetation.PINE),
        OAK(Vegetation.OAK), WILLOW(Vegetation.WETLAND), WATER(Vegetation.WETLAND);

        private final Vegetation vegetation;

        Band(Vegetation vegetation) { this.vegetation = vegetation; }

        public Vegetation vegetation() { return vegetation; }

        /** Old growth (oak wood, willow carr) counts toward restoration; it barely burns or not at all. */
        public boolean oldGrowth() { return this == OAK || this == WILLOW; }
    }

    public enum Outcome { RESTORED, GROWING, SCORCHED }

    /**
     * Tuning. Distances are in cells.
     *
     * @param yearsPerSeason growth years per season
     * @param seedReach      ash greens only with a living cell within this many cells (Chebyshev)
     * @param cacheRadius    an ark seed cache plants meadow within this radius
     * @param caches         ark seed caches for the whole run
     * @param waterPerSeason water carries per season
     * @param waterRadius    a carry waters this radius for the season
     * @param carryCells     water can be carried at most this far from a water cell
     * @param waterBoost     growth multiplier on watered cells
     * @param herds          grazing herds for the whole run (placed herds stay)
     * @param grazeRadius    a herd crops this radius
     * @param strikeChance   lightning chance per season at full fuel (scaled by the fuel load)
     * @param dryWind        dry-season wind strength 0..1 behind a lightning fire (random direction each strike)
     * @param maxFireTicks   a fire is fought out after at most this many ticks
     * @param oldGrowthTarget restored when this share of land is old growth (oak, willow)
     * @param scorchedAt     scorched when fires have burnt this share of the land in total
     * @param maxSeasons     the run ends after this many seasons
     */
    public record Settings(double yearsPerSeason, int seedReach, int cacheRadius, int caches, int waterPerSeason,
            int waterRadius, int carryCells, double waterBoost, int herds, int grazeRadius, double strikeChance,
            double dryWind, int maxFireTicks, double oldGrowthTarget, double scorchedAt, int maxSeasons) {

        public static final Settings DEFAULT =
                new Settings(4.0, 2, 1, 6, 3, 1, 4, 2.0, 2, 1, 1.0, 1.0, 200, 0.4, 0.75, 40);

        public Settings {
            if (!(yearsPerSeason > 0) || seedReach < 1 || cacheRadius < 0 || caches < 0 || waterPerSeason < 0
                    || waterRadius < 0 || carryCells < 0 || !(waterBoost >= 1) || herds < 0 || grazeRadius < 0
                    || !(strikeChance >= 0 && strikeChance <= 1) || !(dryWind >= 0 && dryWind <= 1) || maxFireTicks < 1
                    || !(oldGrowthTarget > 0 && oldGrowthTarget <= 1) || !(scorchedAt > 0 && scorchedAt <= 1)
                    || maxSeasons < 1) {
                throw new IllegalArgumentException("bad AshfallRegrowth settings");
            }
        }
    }

    /** What one season did: cells that climbed a band, whether lightning struck, and what burnt. */
    public record Season(int index, int grown, boolean struck, int strikeI, int strikeJ, int burnt, double fuel) {}

    /** End-of-run summary. */
    public record Report(Outcome outcome, int seasons, double oldGrowth, Map<Band, Integer> census, int strikes,
            int burnt, int cachesUsed, int herdsPlaced) {
        public Report {
            census = Map.copyOf(census);
        }
    }

    private final BattlefieldEcology field;
    private final Settings s;
    private final SplittableRandom rng;
    private final int w;
    private final int h;
    private final Band[] band;
    private final double[] age;
    private final boolean[] grazed;
    private final boolean[] wateredNow;
    private final int[] waterDist;
    private final int land;
    private int cachesUsed;
    private int herdsPlaced;
    private int waterUsed;
    private int seasons;
    private int strikes;
    private int burntTotal;

    private AshfallRegrowth(BattlefieldEcology field, Settings s, long seed) {
        this.field = field;
        this.s = s;
        this.rng = new SplittableRandom(seed);
        this.w = field.width();
        this.h = field.height();
        this.band = new Band[w * h];
        this.age = new double[w * h];
        this.grazed = new boolean[w * h];
        this.wateredNow = new boolean[w * h];
        int n = 0;
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                int k = j * w + i;
                if (field.vegetation(i, j) == Vegetation.WETLAND) {
                    band[k] = Band.WATER;
                } else {
                    band[k] = Band.ASH;
                    n++;
                }
                paint(i, j);
            }
        }
        this.land = n;
        this.waterDist = waterDistances();
    }

    /**
     * The impact: scorches every non-water cell of the fragment to ash. The field is used as the live fire field from
     * here on, so a host reading it (cover, concealment, DBE 1 snapshots) sees the recovery.
     */
    public static AshfallRegrowth scorch(BattlefieldEcology field, Settings settings, long seed) {
        if (field == null || settings == null) {
            throw new IllegalArgumentException("field and settings are required");
        }
        return new AshfallRegrowth(field, settings, seed);
    }

    // ---- player tools -------------------------------------------------------------------------------------------

    /** Opens an ark seed cache at a world point. Returns the cells planted, or -1 when no caches are left. */
    public int seedCache(double x, double y) {
        if (cachesUsed >= s.caches()) {
            return -1;
        }
        cachesUsed++;
        int planted = 0;
        for (int k : around(field.cellI(x), field.cellJ(y), s.cacheRadius())) {
            if (band[k] == Band.ASH) {
                set(k, Band.MEADOW);
                planted++;
            }
        }
        return planted;
    }

    /**
     * Carries water to a patch for this season. Refused (false) when no carries are left this season or the patch is
     * further than {@code carryCells} from water.
     */
    public boolean water(double x, double y) {
        int ci = field.cellI(x);
        int cj = field.cellJ(y);
        if (waterUsed >= s.waterPerSeason() || distanceToWater(ci, cj) > s.carryCells()) {
            return false;
        }
        waterUsed++;
        for (int k : around(ci, cj, s.waterRadius())) {
            wateredNow[k] = true;
        }
        return true;
    }

    /** Sets a grazing herd on a patch for the rest of the run. False when no herds are left. */
    public boolean graze(double x, double y) {
        if (herdsPlaced >= s.herds()) {
            return false;
        }
        herdsPlaced++;
        for (int k : around(field.cellI(x), field.cellJ(y), s.grazeRadius())) {
            if (band[k] != Band.WATER) {
                grazed[k] = true;
                if (band[k] == Band.BRAMBLE) {
                    set(k, Band.MEADOW);
                }
            }
        }
        return true;
    }

    // ---- time ---------------------------------------------------------------------------------------------------

    /** One season: growth, then maybe a dry-season lightning strike. Watering ends with the season. */
    public Season season() {
        int grown = grow();
        double fuel = fuel();
        boolean struck = false;
        int si = -1;
        int sj = -1;
        int burnt = 0;
        if (rng.nextDouble() < s.strikeChance() * fuel) {
            int[] cell = pickStrike();
            if (cell != null) {
                struck = true;
                double a = rng.nextDouble() * 2 * Math.PI;
                field.wind(s.dryWind() * Math.cos(a), s.dryWind() * Math.sin(a));
                si = cell[0];
                sj = cell[1];
                burnt = burn(si, sj);
            }
        }
        Arrays.fill(wateredNow, false);
        waterUsed = 0;
        seasons++;
        return new Season(seasons, grown, struck, si, sj, burnt, fuel);
    }

    /**
     * Lightning (or a combat fire) at a cell, fought out with the battlefield fire rules under the field's current
     * wind. Watered and grazed cells do not carry fire. Returns the land cells burnt back to ash.
     */
    public int strike(double x, double y) {
        return burn(field.cellI(x), field.cellJ(y));
    }

    /** Sets the wind on the fire field (each component -1..1), e.g. for a scripted or combat fire. */
    public AshfallRegrowth wind(double x, double y) {
        field.wind(x, y);
        return this;
    }

    /** Plays seasons until restored, scorched or out of seasons, calling the plan before each season. */
    public Report play(Plan plan) {
        while (outcome() == Outcome.GROWING && seasons < s.maxSeasons()) {
            if (plan != null) {
                plan.before(this, seasons);
            }
            season();
        }
        return report();
    }

    /** The player's moves before a season (seed caches, water carries, herds). */
    @FunctionalInterface
    public interface Plan {
        void before(AshfallRegrowth game, int season);
    }

    // ---- queries ------------------------------------------------------------------------------------------------

    public Band band(int i, int j) { return band[index(i, j)]; }
    public boolean grazed(int i, int j) { return grazed[index(i, j)]; }
    public int seasons() { return seasons; }
    public int land() { return land; }
    public int cachesLeft() { return s.caches() - cachesUsed; }
    public int herdsLeft() { return s.herds() - herdsPlaced; }

    /** Share of land cells that are old growth (oak or willow). */
    public double oldGrowth() {
        int c = 0;
        for (Band b : band) {
            if (b.oldGrowth()) {
                c++;
            }
        }
        return land == 0 ? 0 : (double) c / land;
    }

    /** Fuel load 0..1: mean flammability of land that would carry fire (grazed and watered cells excluded). */
    public double fuel() {
        if (land == 0) {
            return 0;
        }
        double f = 0;
        for (int k = 0; k < band.length; k++) {
            if (band[k] != Band.WATER && !firebreak(k)) {
                f += band[k].vegetation().flammability();
            }
        }
        return f / land;
    }

    public Outcome outcome() {
        if (land > 0 && burntTotal >= s.scorchedAt() * land) {
            return Outcome.SCORCHED;
        }
        return oldGrowth() >= s.oldGrowthTarget() ? Outcome.RESTORED : Outcome.GROWING;
    }

    public Report report() {
        Map<Band, Integer> census = new EnumMap<>(Band.class);
        for (Band b : Band.values()) {
            census.put(b, 0);
        }
        for (Band b : band) {
            census.merge(b, 1, Integer::sum);
        }
        return new Report(outcome(), seasons, oldGrowth(), census, strikes, burntTotal, cachesUsed, herdsPlaced);
    }

    // ---- internals ----------------------------------------------------------------------------------------------

    private int grow() {
        int grown = 0;
        Band[] before = band.clone();
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                int k = j * w + i;
                Band b = before[k];
                if (b == Band.WATER || b == Band.OAK || b == Band.WILLOW) {
                    continue;
                }
                if (b == Band.ASH && !seedRain(before, i, j)) {
                    continue;
                }
                if (grazed[k] && b == Band.MEADOW) {
                    continue;   // cropped turf holds at meadow
                }
                age[k] += s.yearsPerSeason() * (wateredNow[k] ? s.waterBoost() : 1);
                double need = b.vegetation().yearsToNext();
                if (age[k] >= need) {
                    double carry = age[k] - need;
                    Band nb = next(b, i, j);
                    if (grazed[k] && nb == Band.BRAMBLE) {
                        nb = Band.MEADOW;
                    }
                    if (nb != b) {
                        set(k, nb);
                        age[k] = Math.min(carry, s.yearsPerSeason());
                        grown++;
                    }
                }
            }
        }
        return grown;
    }

    private Band next(Band b, int i, int j) {
        return switch (b) {
            case ASH -> Band.MEADOW;
            case MEADOW -> distanceToWater(i, j) <= 1 ? Band.WILLOW : Band.BRAMBLE;
            case BRAMBLE -> Band.PINE;
            case PINE -> Band.OAK;
            case OAK, WILLOW, WATER -> b;
        };
    }

    private boolean seedRain(Band[] snapshot, int ci, int cj) {
        int r = s.seedReach();
        for (int j = Math.max(0, cj - r); j <= Math.min(h - 1, cj + r); j++) {
            for (int i = Math.max(0, ci - r); i <= Math.min(w - 1, ci + r); i++) {
                Band b = snapshot[j * w + i];
                if (b != Band.ASH && b != Band.WATER) {
                    return true;
                }
            }
        }
        return false;
    }

    private int[] pickStrike() {
        List<int[]> fuelCells = new ArrayList<>();
        for (int j = 0; j < h; j++) {
            for (int i = 0; i < w; i++) {
                int k = j * w + i;
                if (band[k] != Band.WATER && band[k].vegetation().flammability() > 0) {
                    fuelCells.add(new int[] {i, j});
                }
            }
        }
        return fuelCells.isEmpty() ? null : fuelCells.get(rng.nextInt(fuelCells.size()));
    }

    private int burn(int ci, int cj) {
        int k0 = index(ci, cj);
        strikes++;
        if (band[k0] == Band.WATER || firebreak(k0)) {
            return 0;
        }
        field.apply(BattlefieldEcology.EventKind.IGNITE, field.centreX(ci), field.centreY(cj), 0);
        for (int t = 0; t < s.maxFireTicks(); t++) {
            boolean any = false;
            for (int k = 0; k < band.length; k++) {
                int i = k % w;
                int j = k / w;
                if (field.burning(i, j) > 0) {
                    if (firebreak(k)) {
                        field.apply(BattlefieldEcology.EventKind.DOUSE, field.centreX(i), field.centreY(j), 0);
                    } else {
                        any = true;
                    }
                }
            }
            if (!any) {
                break;
            }
            field.tick();
        }
        // whatever is still alight at the end is fought out
        for (int k = 0; k < band.length; k++) {
            int i = k % w;
            int j = k / w;
            if (field.burning(i, j) > 0) {
                field.apply(BattlefieldEcology.EventKind.DOUSE, field.centreX(i), field.centreY(j), 0);
            }
        }
        int burnt = 0;
        for (int k = 0; k < band.length; k++) {
            int i = k % w;
            int j = k / w;
            if (band[k] != Band.WATER && band[k] != Band.ASH && field.vegetation(i, j) == Vegetation.BARE) {
                band[k] = Band.ASH;
                age[k] = 0;
                burnt++;
            }
        }
        burntTotal += burnt;
        return burnt;
    }

    private boolean firebreak(int k) {
        return grazed[k] || wateredNow[k];
    }

    private int distanceToWater(int ci, int cj) {
        return waterDist[index(ci, cj)];
    }

    /** Chebyshev distance from every cell to the nearest water cell (multi-source breadth-first, 8 neighbours). */
    private int[] waterDistances() {
        int[] d = new int[w * h];
        Arrays.fill(d, Integer.MAX_VALUE);
        ArrayDeque<Integer> q = new ArrayDeque<>();
        for (int k = 0; k < band.length; k++) {
            if (band[k] == Band.WATER) {
                d[k] = 0;
                q.add(k);
            }
        }
        while (!q.isEmpty()) {
            int k = q.poll();
            int i = k % w;
            int j = k / w;
            for (int dj = -1; dj <= 1; dj++) {
                for (int di = -1; di <= 1; di++) {
                    int ni = i + di;
                    int nj = j + dj;
                    if (ni >= 0 && nj >= 0 && ni < w && nj < h && d[nj * w + ni] == Integer.MAX_VALUE) {
                        d[nj * w + ni] = d[k] + 1;
                        q.add(nj * w + ni);
                    }
                }
            }
        }
        return d;
    }

    private List<Integer> around(int ci, int cj, int r) {
        List<Integer> out = new ArrayList<>();
        for (int j = Math.max(0, cj - r); j <= Math.min(h - 1, cj + r); j++) {
            for (int i = Math.max(0, ci - r); i <= Math.min(w - 1, ci + r); i++) {
                out.add(j * w + i);
            }
        }
        return out;
    }

    private void set(int k, Band b) {
        band[k] = b;
        age[k] = 0;
        paint(k % w, k / w);
    }

    private void paint(int i, int j) {
        field.set(i, j, band[j * w + i].vegetation());
    }

    private int index(int i, int j) {
        if (i < 0 || j < 0 || i >= w || j >= h) {
            throw new IndexOutOfBoundsException("cell " + i + "," + j + " outside " + w + "x" + h);
        }
        return j * w + i;
    }
}
