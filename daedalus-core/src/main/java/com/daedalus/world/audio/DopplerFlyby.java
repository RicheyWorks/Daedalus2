// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Doppler Flyby (contest G96): arks shuttle life off the planet, and the island hears who is passing.
 *
 * <p>A seeded roster of 4-6 arks (names from {@link FogBellCallSigns#ARKS}) each sound a horn on its own
 * equal-tempered pitch from A2 up two octaves (distinct semitones). One ark sweeps past the listening post
 * at a seeded speed (20-120 m/s); the post hears the approach pitch {@code fa = f0 c/(c - v)} and the
 * recede pitch {@code fr = f0 c/(c + v)}, each rounded to 0.1 Hz. The player names the ark (true horn
 * {@code f0 = 2 fa fr/(fa + fr)}) and its speed ({@code v = c (fa - fr)/(fa + fr)}, within
 * {@link #SPEED_TOLERANCE} m/s).
 */
public final class DopplerFlyby {
    /** Speed of sound, m/s. */
    public static final double C = 343.0;
    /** Allowed speed error, m/s. */
    public static final double SPEED_TOLERANCE = 1.0;
    private static final long SALT = 0x4450_4631L; // "DPF1"

    /** One ark and its horn. */
    public record Ark(String name, double hornHz) { }

    /** A judged answer. */
    public record Verdict(boolean correct, boolean rightArk, boolean rightSpeed, String ark, int speed) { }

    private final long seed;
    private final List<Ark> roster;
    private final int passing;
    private final int speed;

    private DopplerFlyby(long seed, List<Ark> roster, int passing, int speed) {
        this.seed = seed;
        this.roster = List.copyOf(roster);
        this.passing = passing;
        this.speed = speed;
    }

    /** A seeded flyby. */
    public static DopplerFlyby seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int n = 4 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
        List<String> names = new ArrayList<>(FogBellCallSigns.ARKS);
        List<Integer> semis = new ArrayList<>();
        for (int i = 0; i < 24; i++) {
            semis.add(i);
        }
        List<Ark> roster = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            String name = names.remove((int) Long.remainderUnsigned(rng.nextLong(), names.size()));
            int k = semis.remove((int) Long.remainderUnsigned(rng.nextLong(), semis.size()));
            roster.add(new Ark(name, round3(110.0 * Math.pow(2, k / 12.0))));
        }
        int passing = (int) Long.remainderUnsigned(rng.nextLong(), n);
        int speed = 20 + (int) Long.remainderUnsigned(rng.nextLong(), 101);
        return new DopplerFlyby(seed, roster, passing, speed);
    }

    private static double round3(double v) {
        return Math.round(v * 1000) / 1000.0;
    }

    private static double round1(double v) {
        return Math.round(v * 10) / 10.0;
    }

    /** Approach pitch of a horn {@code f0} at speed {@code v}. */
    public static double approachHz(double f0, double v) {
        return f0 * C / (C - v);
    }

    /** Recede pitch of a horn {@code f0} at speed {@code v}. */
    public static double recedeHz(double f0, double v) {
        return f0 * C / (C + v);
    }

    /** True horn pitch from the two heard pitches. */
    public static double hornFrom(double fa, double fr) {
        return 2 * fa * fr / (fa + fr);
    }

    /** Speed from the two heard pitches. */
    public static double speedFrom(double fa, double fr) {
        return C * (fa - fr) / (fa + fr);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The roster. */
    public List<Ark> roster() {
        return roster;
    }

    /** Heard approach pitch (0.1 Hz). */
    public double heardApproach() {
        return round1(approachHz(roster.get(passing).hornHz(), speed));
    }

    /** Heard recede pitch (0.1 Hz). */
    public double heardRecede() {
        return round1(recedeHz(roster.get(passing).hornHz(), speed));
    }

    /** Roster ark whose horn is nearest (in log pitch) to {@code hz}. */
    public String nearestArk(double hz) {
        Ark best = roster.get(0);
        for (Ark a : roster) {
            if (Math.abs(Math.log(a.hornHz() / hz)) < Math.abs(Math.log(best.hornHz() / hz))) {
                best = a;
            }
        }
        return best.name();
    }

    /** Judge the player's ark and speed. */
    public Verdict judge(String ark, double speedGuess) {
        String truth = roster.get(passing).name();
        boolean a = truth.equals(ark);
        boolean s = Math.abs(speedGuess - speed) <= SPEED_TOLERANCE;
        return new Verdict(a && s, a, s, truth, speed);
    }
}