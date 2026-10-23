// SPDX-License-Identifier: MIT

package com.daedalus.world.sports;

import com.daedalus.world.companion.MiniJson;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Throwables sports minigame core (WZ25, contest gap G11): catch, basketball and baseball scoring for the
 * {@code Prop_Sport_*} throwable props. Pure, JDK-only, deterministic per seed. Rules live in
 * {@code data/sports/throwables-v1.json}. Separate from the Dodge Ball arcade cabinet.
 *
 * <p>Daedalus tie-in: companions and pets can play. A pet catcher gets the {@code petFetchBonus} on fetch balls
 * (frisbee, tennis, soccer, beach, dodgeballs), so a Kennel Isle dog is a real festival teammate.
 */
public final class ThrowableSports {
    public record Ball(String prop, String kind, double catchDifficulty, boolean fetch) { }

    public record CatchRules(double maxRangeM, double rangePenaltyPerM, int streakBonusEvery, double petFetchBonus) { }

    public record HoopRules(double threePointLineM, double maxShotM, double layupPct, double dropPerM) { }

    public record BatRules(int perfectMs, int goodMs, int foulMs, int strikesPerOut, int outsPerInning) { }

    /** A player or companion. skill is 0..1. */
    public record Player(String name, double skill, boolean pet) {
        public Player {
            if (skill < 0 || skill > 1) {
                throw new IllegalArgumentException("skill must be 0..1");
            }
        }
    }

    private final Map<String, Ball> balls;
    private final CatchRules catchRules;
    private final HoopRules hoop;
    private final BatRules bat;

    public ThrowableSports(Map<String, Ball> balls, CatchRules c, HoopRules h, BatRules b) {
        this.balls = Collections.unmodifiableMap(new TreeMap<>(balls));
        this.catchRules = c;
        this.hoop = h;
        this.bat = b;
    }

    public static ThrowableSports load(Path p) throws IOException {
        return parse(Files.readString(p, StandardCharsets.UTF_8));
    }

    @SuppressWarnings("unchecked")
    public static ThrowableSports parse(String json) {
        Map<String, Object> r = (Map<String, Object>) MiniJson.parse(json);
        if (!(r.get("version") instanceof Number v) || v.intValue() != 1) {
            throw new IllegalArgumentException("throwables version must be 1");
        }
        Map<String, Ball> balls = new TreeMap<>();
        for (Map.Entry<String, Object> e : ((Map<String, Object>) r.get("balls")).entrySet()) {
            Map<String, Object> b = (Map<String, Object>) e.getValue();
            String kind = (String) b.get("kind");
            if (!List.of("catch", "basketball", "baseball").contains(kind)) {
                throw new IllegalArgumentException("bad ball kind " + kind);
            }
            balls.put(e.getKey(), new Ball(e.getKey(), kind, n(b, "catchDifficulty"), (Boolean) b.get("fetch")));
        }
        Map<String, Object> c = (Map<String, Object>) r.get("catch");
        Map<String, Object> h = (Map<String, Object>) r.get("basketball");
        Map<String, Object> b = (Map<String, Object>) r.get("baseball");
        return new ThrowableSports(balls,
            new CatchRules(n(c, "maxRangeM"), n(c, "rangePenaltyPerM"), (int) n(c, "streakBonusEvery"), n(c, "petFetchBonus")),
            new HoopRules(n(h, "threePointLineM"), n(h, "maxShotM"), n(h, "layupPct"), n(h, "dropPerM")),
            new BatRules((int) n(b, "perfectMs"), (int) n(b, "goodMs"), (int) n(b, "foulMs"), (int) n(b, "strikesPerOut"),
                (int) n(b, "outsPerInning")));
    }

    private static double n(Map<String, Object> m, String k) {
        if (!(m.get(k) instanceof Number x)) {
            throw new IllegalArgumentException("throwables missing number " + k);
        }
        return x.doubleValue();
    }

    public Map<String, Ball> balls() {
        return balls;
    }

    public Ball ball(String prop) {
        Ball b = balls.get(prop);
        if (b == null) {
            throw new IllegalArgumentException("not a throwable: " + prop);
        }
        return b;
    }

    // ---- catch ----

    /** Probability the catcher holds a throw at {@code distanceM}. 0 beyond max range. */
    public double catchChance(Player catcher, Ball ball, double distanceM) {
        if (distanceM < 0 || distanceM > catchRules.maxRangeM()) {
            return 0;
        }
        double p = 0.5 + 0.5 * catcher.skill() - ball.catchDifficulty() - catchRules.rangePenaltyPerM() * distanceM;
        if (catcher.pet() && ball.fetch()) {
            p += catchRules.petFetchBonus();
        }
        return clamp(p);
    }

    public record CatchResult(int score, int caught, int bestStreak, List<Boolean> log) {
        public CatchResult {
            log = List.copyOf(log);
        }
    }

    /** A catch rally: each throw is 1 point when caught, plus 1 bonus on every Nth consecutive catch. */
    public CatchResult playCatch(Player catcher, String prop, List<Double> throwsM, long seed) {
        Ball ball = ball(prop);
        int score = 0;
        int caught = 0;
        int streak = 0;
        int best = 0;
        Boolean[] log = new Boolean[throwsM.size()];
        for (int i = 0; i < throwsM.size(); i++) {
            boolean ok = roll(seed, i, 1) < catchChance(catcher, ball, throwsM.get(i));
            log[i] = ok;
            if (ok) {
                caught++;
                streak++;
                best = Math.max(best, streak);
                score += 1 + (streak % catchRules.streakBonusEvery() == 0 ? 1 : 0);
            } else {
                streak = 0;
            }
        }
        return new CatchResult(score, caught, best, List.of(log));
    }

    // ---- basketball ----

    public double shotChance(Player shooter, double distanceM) {
        if (distanceM < 0 || distanceM > hoop.maxShotM()) {
            return 0;
        }
        return clamp((hoop.layupPct() - hoop.dropPerM() * distanceM) * (0.6 + 0.4 * shooter.skill()));
    }

    /** Points a made shot is worth from {@code distanceM}. */
    public int shotValue(double distanceM) {
        return distanceM >= hoop.threePointLineM() ? 3 : 2;
    }

    /** Total points over a list of shot distances, using the basketball prop. */
    public int playHoops(Player shooter, String prop, List<Double> shotsM, long seed) {
        if (!"basketball".equals(ball(prop).kind())) {
            throw new IllegalArgumentException(prop + " is not a basketball");
        }
        int pts = 0;
        for (int i = 0; i < shotsM.size(); i++) {
            double d = shotsM.get(i);
            if (roll(seed, i, 2) < shotChance(shooter, d)) {
                pts += shotValue(d);
            }
        }
        return pts;
    }

    // ---- baseball ----

    public enum Swing { HOME_RUN, DOUBLE, SINGLE, FOUL, STRIKE }

    /** Swing timing (ms off the perfect moment; null = no swing, counts as a strike) to outcome. */
    public Swing swing(Integer offsetMs) {
        if (offsetMs == null) {
            return Swing.STRIKE;
        }
        long a = Math.abs((long) offsetMs);
        if (a <= bat.perfectMs()) {
            return Swing.HOME_RUN;
        }
        if (a <= bat.goodMs()) {
            return offsetMs < 0 ? Swing.DOUBLE : Swing.SINGLE;
        }
        if (a <= bat.foulMs()) {
            return Swing.FOUL;
        }
        return Swing.STRIKE;
    }

    public record Inning(int runs, int outs, int hits, int pitches) { }

    /**
     * Plays one half-inning from a list of swing offsets. Bases advance by the hit's base count (forced runners score);
     * fouls add a strike only below two strikes. Stops at {@code outsPerInning} outs or when the swings run out.
     */
    public Inning playInning(String prop, List<Integer> swings) {
        if (!"baseball".equals(ball(prop).kind())) {
            throw new IllegalArgumentException(prop + " is not a baseball");
        }
        boolean[] bases = new boolean[3];
        int runs = 0;
        int outs = 0;
        int hits = 0;
        int strikes = 0;
        int pitches = 0;
        for (Integer off : swings) {
            if (outs >= bat.outsPerInning()) {
                break;
            }
            pitches++;
            Swing s = swing(off);
            switch (s) {
                case STRIKE -> {
                    if (++strikes >= bat.strikesPerOut()) {
                        outs++;
                        strikes = 0;
                    }
                }
                case FOUL -> {
                    if (strikes < bat.strikesPerOut() - 1) {
                        strikes++;
                    }
                }
                default -> {
                    hits++;
                    strikes = 0;
                    int n = s == Swing.HOME_RUN ? 4 : s == Swing.DOUBLE ? 2 : 1;
                    runs += advance(bases, n);
                }
            }
        }
        return new Inning(runs, outs, hits, pitches);
    }

    static int advance(boolean[] bases, int n) {
        int runs = 0;
        for (int b = 2; b >= 0; b--) {
            if (bases[b]) {
                bases[b] = false;
                int to = b + n;
                if (to >= 3) {
                    runs++;
                } else {
                    bases[to] = true;
                }
            }
        }
        if (n >= 4) {
            runs++;
        } else {
            bases[n - 1] = true;
        }
        return runs;
    }

    private static double clamp(double p) {
        return Math.max(0, Math.min(1, p));
    }

    static double roll(long seed, int i, int salt) {
        long z = seed * 0x9E3779B97F4A7C15L + i * 0xC2B2AE3D27D4EB4FL + salt;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z ^= z >>> 31;
        return (z >>> 11) * 0x1.0p-53;
    }
}
