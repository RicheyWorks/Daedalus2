// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

/**
 * Mark-Recapture census (contest G156, "Tag and Count"): how many thistle hares live on the Ark Refuge?
 *
 * <p>Census-keeper Orrin Vale has {@code traps} trap-nights. The player splits them across two sessions
 * ({@link #plan(int, int)}). In session 1 every hare caught is ear-tagged and let go. Between sessions some hares die and
 * are replaced by untagged young ({@code turnover}), and some tags fall off ({@code tagLoss}). In session 2 every hare
 * caught is checked for a tag. A hare is caught in a session with chance {@code 1 − (1 − perTrap)^t} for {@code t}
 * trap-nights; hares caught in session 1 have that chance scaled by {@code trapResponse} in session 2 (above 1 they are
 * trap-happy, below 1 trap-shy).
 *
 * <p>From the marked count M, the session-2 catch C and the recaptures R, the census gives the Lincoln-Petersen estimate
 * {@code M·C/R}, the Chapman estimate {@code (M+1)(C+1)/(R+1) − 1}, its Seber variance and a 95% band. Tag loss,
 * turnover and trap-shy hares lower R and inflate the count; trap-happy hares raise R and shrink it. Every draw is a
 * splitmix hash of (seed, session, hare, salt).
 */
public final class MarkRecapture {

    /** How close the Chapman count came to the true population. */
    public enum Verdict { ACCURATE, ROUGH, MISLEADING }

    /** Error bands for {@link Verdict}: within 15% is ACCURATE, within 35% ROUGH. */
    public static final double ACCURATE = 0.15;

    /** See {@link #ACCURATE}. */
    public static final double ROUGH = 0.35;

    /**
     * Refuge tuning.
     *
     * @param population   true number of hares (hidden from the player)
     * @param traps        trap-nights Vale can spend across both sessions
     * @param perTrap      chance one trap-night catches a given hare
     * @param tagLoss      chance a tag falls off between sessions
     * @param trapResponse session-2 catch multiplier for hares caught in session 1
     * @param turnover     chance a hare dies between sessions and is replaced by an untagged young one
     */
    public record Settings(int population, int traps, double perTrap, double tagLoss, double trapResponse,
            double turnover) {

        /** The default refuge: 240 hares, 60 trap-nights, honest tags and hares. */
        public static final Settings DEFAULT = new Settings(240, 60, 0.012, 0, 1, 0);

        /** Rejects tuning that cannot run. */
        public Settings {
            if (population < 1 || traps < 2 || !(perTrap > 0 && perTrap < 1) || !(tagLoss >= 0 && tagLoss <= 1)
                    || !(trapResponse >= 0) || Double.isInfinite(trapResponse) || !(turnover >= 0 && turnover <= 1)) {
                throw new IllegalArgumentException("bad mark-recapture settings");
            }
        }

        /** A copy with other biases. */
        public Settings with(double newTagLoss, double newTrapResponse, double newTurnover) {
            return new Settings(population, traps, perTrap, newTagLoss, newTrapResponse, newTurnover);
        }
    }

    /**
     * One census.
     *
     * @param marked      M, hares tagged in session 1
     * @param caught      C, hares caught in session 2
     * @param recaptured  R, session-2 hares that still carried a tag
     * @param truth       the true population (for judging only, never shown on Vale's board)
     */
    public record Census(int marked, int caught, int recaptured, int truth) {

        /** Lincoln-Petersen M·C/R; positive infinity with no recaptures. */
        public double lincolnPetersen() {
            return MarkRecapture.lincolnPetersen(marked, caught, recaptured);
        }

        /** Chapman (M+1)(C+1)/(R+1) − 1, finite even with no recaptures. */
        public double chapman() {
            return MarkRecapture.chapman(marked, caught, recaptured);
        }

        /** Seber variance of the Chapman estimate. */
        public double variance() {
            return MarkRecapture.seberVariance(marked, caught, recaptured);
        }

        /** Lower end of the 95% band, never below the hares actually handled (M + C − R). */
        public double low() {
            return Math.max(handled(), chapman() - 1.96 * Math.sqrt(variance()));
        }

        /** Upper end of the 95% band. */
        public double high() {
            return Math.max(low(), chapman() + 1.96 * Math.sqrt(variance()));
        }

        /** Distinct-looking hares handled across both sessions. */
        public int handled() {
            return marked + caught - recaptured;
        }

        /** Relative error of the Chapman count against the truth. */
        public double error() {
            return (chapman() - truth) / truth;
        }

        /** ACCURATE within 15%, ROUGH within 35%, otherwise MISLEADING. */
        public Verdict verdict() {
            double e = Math.abs(error());
            return e <= ACCURATE ? Verdict.ACCURATE : e <= ROUGH ? Verdict.ROUGH : Verdict.MISLEADING;
        }

        /** Vale's harvest quota: {@code rate} of the band's lower end, rounded down. */
        public int quota(double rate) {
            return (int) Math.floor(rate * low());
        }

        /** The quota Vale would set from the point estimate instead. */
        public int greedyQuota(double rate) {
            return (int) Math.floor(rate * chapman());
        }

        /** True if a harvest of {@code take} is no more than {@code rate} of the true population. */
        public boolean safe(int take, double rate) {
            return take <= rate * truth;
        }

        /** Refuge cover after the harvest: a safe quota keeps the meadow MEADOW, an overharvest lets it scrub over. */
        public Vegetation band(double rate) {
            return safe(quota(rate), rate) ? Vegetation.MEADOW : Vegetation.SCRUB;
        }
    }

    private final Settings s;
    private final long seed;
    private int first;
    private int second;

    private MarkRecapture(Settings s, long seed) {
        this.s = s;
        this.seed = seed;
    }

    /** A seeded refuge. */
    public static MarkRecapture refuge(Settings settings, long seed) {
        if (settings == null) {
            throw new IllegalArgumentException("settings");
        }
        return new MarkRecapture(settings, seed);
    }

    /** Splits trap-nights across the sessions. False (plan unchanged) unless both are at least 1 and fit the budget. */
    public boolean plan(int trapsFirst, int trapsSecond) {
        if (trapsFirst < 1 || trapsSecond < 1 || (long) trapsFirst + trapsSecond > s.traps()) {
            return false;
        }
        first = trapsFirst;
        second = trapsSecond;
        return true;
    }

    /** Catch chance for one hare in a session of {@code t} trap-nights. */
    public double catchChance(int t) {
        return 1 - Math.pow(1 - s.perTrap(), t);
    }

    /** Runs both sessions. Deterministic in the settings, the seed and the plan; an unplanned census splits evenly. */
    public Census run() {
        int t1 = first;
        int t2 = second;
        if (t1 == 0) {
            t1 = s.traps() / 2;
            t2 = s.traps() - t1;
        }
        double p1 = catchChance(t1);
        double p2 = catchChance(t2);
        double p2Caught = Math.min(1, p2 * s.trapResponse());
        int m = 0;
        int c = 0;
        int r = 0;
        for (int h = 0; h < s.population(); h++) {
            boolean caughtOnce = roll(1, h, 1) < p1;
            if (caughtOnce) {
                m++;
            }
            boolean replaced = roll(1, h, 2) < s.turnover();
            boolean tagged = caughtOnce && !replaced && !(roll(1, h, 3) < s.tagLoss());
            double p = caughtOnce && !replaced ? p2Caught : p2;
            if (roll(2, h, 4) < p) {
                c++;
                if (tagged) {
                    r++;
                }
            }
        }
        return new Census(m, c, r, s.population());
    }

    /** Lincoln-Petersen M·C/R; positive infinity when R is 0. */
    public static double lincolnPetersen(int m, int c, int r) {
        check(m, c, r);
        return r == 0 ? Double.POSITIVE_INFINITY : (double) m * c / r;
    }

    /** Chapman (M+1)(C+1)/(R+1) − 1. */
    public static double chapman(int m, int c, int r) {
        check(m, c, r);
        return (m + 1.0) * (c + 1.0) / (r + 1.0) - 1;
    }

    /** Seber variance (M+1)(C+1)(M−R)(C−R) / ((R+1)²(R+2)). */
    public static double seberVariance(int m, int c, int r) {
        check(m, c, r);
        return (m + 1.0) * (c + 1.0) * (m - r) * (c - r) / ((r + 1.0) * (r + 1.0) * (r + 2.0));
    }

    private static void check(int m, int c, int r) {
        if (m < 0 || c < 0 || r < 0 || r > m || r > c) {
            throw new IllegalArgumentException("need 0 <= R <= min(M, C)");
        }
    }

    private double roll(int session, long hare, int salt) {
        long z = seed + 0x9E3779B97F4A7C15L * (session + 1) + 0xBF58476D1CE4E5B9L * (hare + 1) + 0x94D049BB133111EBL * salt;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z = z ^ (z >>> 31);
        return (z >>> 11) * 0x1.0p-53;
    }
}
