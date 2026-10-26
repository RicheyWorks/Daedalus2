// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.List;

/**
 * Bat Ranging (contest G169): at dusk a bat hunts a moth over the regrown pond, and a bat detector replays its
 * calls time-expanded so people can hear them.
 *
 * <p>Each call's echo comes back from the moth after a delay. The bat flies toward the moth while the sound is out,
 * so the echo meets it early: c tau = 2d - v tau, tau = 2d / (c + v), where d is the range when the call leaves and
 * v the closing speed. As the bat closes in, it calls faster: search calls about once per wingbeat, approach calls
 * spaced in proportion to range, then the terminal feeding buzz. The gap to the next call always stays longer than
 * the echo delay, so an echo never overlaps the next call. The player reads the range at a few marked calls and
 * names each call's phase. {@link #solve()} first takes naive ranges c tau / 2, fits their slope over time to get
 * the closing speed, then corrects every range with d = (c + v) tau / 2; phases come from the call spacing.
 *
 * <p>Caveats: real bat echolocation is ultrasonic, roughly 20 to over 100 kHz depending on species (many
 * insect-hunting bats sweep about 25-50 kHz; this game uses 45-50 kHz down to 25-28 kHz). Real time-expansion
 * detectors slow calls about 10 times; here the replay factor {@link #REPLAY} is far larger, so the game pitch is
 * heavily compressed to below 800 Hz and passes {@link EarRule#check}, and it plays soft. The phase ranges, call
 * spacings and their split points, closing speeds and the stationary moth are illustrative; real bats vary call
 * spacing and sweep shape by species, clutter and target. Speed of sound defaults to 20 C air
 * (c = 331.3 + 0.606 T); a night from {@link CricketThermometer} may be passed in (opt-in, one-way).
 */
public final class BatRanging {
    /** Time-expansion replay factor (illustrative; real detectors use about 10). */
    public static final double REPLAY = 80.0;
    /** Default air temperature, C. */
    public static final double DEFAULT_TEMP_C = 20.0;
    /** Search phase above this range, m (illustrative). */
    public static final double APPROACH_M = 3.0;
    /** Terminal buzz at or below this range, m (illustrative). */
    public static final double BUZZ_M = 0.5;
    /** The moth is caught at this range, m. */
    public static final double CATCH_M = 0.05;
    /** Search call spacing, s (about one call per wingbeat). */
    public static final double SEARCH_IPI_S = 0.100;
    /** Approach call spacing per metre of range, s/m (illustrative). */
    public static final double APPROACH_S_PER_M = 0.030;
    /** Buzz call spacing, s (illustrative). */
    public static final double BUZZ_IPI_S = 0.006;
    /** Spacing split between search and approach, s: midway between search spacing and the widest approach spacing. */
    public static final double SEARCH_SPLIT_S = (SEARCH_IPI_S + APPROACH_S_PER_M * APPROACH_M) / 2;
    /** Spacing split between approach and buzz, s: midway between buzz spacing and the tightest approach spacing. */
    public static final double BUZZ_SPLIT_S = (BUZZ_IPI_S + APPROACH_S_PER_M * BUZZ_M) / 2;
    /** The next call never leaves sooner than this after the echo is back, s. */
    public static final double GUARD_S = 0.001;
    /** Echo timing jitter amplitude, s (illustrative detector error). */
    public static final double JITTER_S = 0.00002;
    /** Range tolerance for full marks, m. */
    public static final double TOLERANCE_M = 0.05;
    /** Calls the player must range. */
    public static final int MARKS = 3;
    /** Call level and echo level, 0-1 (soft). */
    public static final double CALL_LEVEL = 0.35;
    /** Echo level, 0-1. */
    public static final double ECHO_LEVEL = 0.12;
    private static final int MAX_CALLS = 1000;
    private static final long SALT = 0x4241_5431L; // "BAT1"

    /** Hunting phase. */
    public enum Phase { SEARCH, APPROACH, BUZZ }

    /** One call: when it left, when its echo came back, its ultrasonic sweep (Hz) and the true range and phase. */
    public record Call(double t, double echoT, double startHz, double endHz, double rangeM, Phase phase) {
        /** Echo delay, s. */
        public double delay() {
            return echoT - t;
        }
    }

    /** One replayed sound for the player (time-expanded and pitched down). */
    public record Sound(double t, double startHz, double endHz, double level, boolean echo) { }

    /** The solver's reading. */
    public record Reading(double closingMps, List<Double> rangesM, List<Phase> phases) {
        /** Copies the lists. */
        public Reading {
            rangesM = List.copyOf(rangesM);
            phases = List.copyOf(phases);
        }
    }

    /** A judged answer. */
    public record Verdict(int rangesRight, int phasesRight, int score) { }

    private final long seed;
    private final double c;
    private final double closing;
    private final List<Call> calls;
    private final double catchT;
    private final List<Integer> marks;

    private BatRanging(long seed, double c, double closing, List<Call> calls, double catchT, List<Integer> marks) {
        this.seed = seed;
        this.c = c;
        this.closing = closing;
        this.calls = List.copyOf(calls);
        this.catchT = catchT;
        this.marks = List.copyOf(marks);
    }

    /** A seeded dusk at the default 20 C. */
    public static BatRanging seeded(long seed) {
        return build(seed, speedOfSound(DEFAULT_TEMP_C), JITTER_S);
    }

    /** A seeded dusk on a {@link CricketThermometer} night (opt-in temperature-aware sound speed). */
    public static BatRanging seeded(long seed, CricketThermometer night) {
        return build(seed, night.speedOfSoundMps(), JITTER_S);
    }

    /** A seeded dusk with chosen sound speed and jitter, for tests. */
    static BatRanging of(long seed, double soundMps, double jitterS) {
        return build(seed, soundMps, jitterS);
    }

    /** Speed of sound in dry air, m/s. */
    public static double speedOfSound(double tempC) {
        return 331.3 + 0.606 * tempC;
    }

    /** Call spacing the bat uses at range {@code d} (always longer than the echo delay plus the guard). */
    public static double spacing(double d, double c, double v) {
        double base;
        if (d > APPROACH_M) {
            base = SEARCH_IPI_S;
        } else if (d > BUZZ_M) {
            base = APPROACH_S_PER_M * d;
        } else {
            base = BUZZ_IPI_S;
        }
        return Math.max(base, echoDelay(d, c, v) + GUARD_S);
    }

    /** Phase at range {@code d}. */
    public static Phase phaseAt(double d) {
        if (d > APPROACH_M) {
            return Phase.SEARCH;
        }
        return d > BUZZ_M ? Phase.APPROACH : Phase.BUZZ;
    }

    /** Echo delay for a call leaving at range {@code d} with closing speed {@code v}: 2d / (c + v). */
    public static double echoDelay(double d, double c, double v) {
        return 2 * d / (c + v);
    }

    private static BatRanging build(long seed, double c, double jitter) {
        Rng rng = new Rng(seed ^ SALT);
        double d0 = 5.0 + roll(rng, 3001) / 1000.0; // 5-8 m
        double v = 3.0 + roll(rng, 2001) / 1000.0; // 3-5 m/s
        double startHz = 45000 + roll(rng, 5001); // 45-50 kHz
        double endHz = 25000 + roll(rng, 3001); // 25-28 kHz
        List<Call> calls = new ArrayList<>();
        double t = 0;
        double catchT = Double.NaN;
        for (int i = 0; i < MAX_CALLS; i++) {
            double d = d0 - v * t;
            if (d <= CATCH_M) {
                catchT = t;
                break;
            }
            double tau = echoDelay(d, c, v) + jitter * (roll(rng, 2001) / 1000.0 - 1.0);
            calls.add(new Call(t, t + tau, startHz, endHz, d, phaseAt(d)));
            double next = t + spacing(d, c, v);
            if (d0 - v * next <= CATCH_M) {
                catchT = t + (d - CATCH_M) / v;
                break;
            }
            t = next;
        }
        List<Integer> marks = new ArrayList<>();
        int n = calls.size();
        for (int k = 0; k < MARKS; k++) {
            int lo = k * n / MARKS;
            int hi = (k + 1) * n / MARKS;
            marks.add(lo + roll(rng, Math.max(1, hi - lo)));
        }
        return new BatRanging(seed, c, v, calls, catchT, marks);
    }

    private static int roll(Rng rng, int n) {
        return (int) Long.remainderUnsigned(rng.nextLong(), n);
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** Speed of sound used tonight, m/s. */
    public double soundMps() {
        return c;
    }

    /** True closing speed, m/s (for the judge and tests). */
    public double closingMps() {
        return closing;
    }

    /** All calls in order (true ranges and phases are for the judge and tests). */
    public List<Call> calls() {
        return calls;
    }

    /** When the moth is caught, s (the last event; no call). */
    public double catchT() {
        return catchT;
    }

    /** Indices of the calls the player must range, one per third of the pass. */
    public List<Integer> marks() {
        return marks;
    }

    /** Replayed sound, time-expanded by {@link #REPLAY} (ear-rule checked), in time order. */
    public List<Sound> replay() {
        List<Sound> out = new ArrayList<>();
        for (Call k : calls) {
            double a = EarRule.check(k.startHz() / REPLAY, "bat call start");
            double b = EarRule.check(k.endHz() / REPLAY, "bat call end");
            out.add(new Sound(k.t() * REPLAY, a, b, CALL_LEVEL, false));
            out.add(new Sound(k.echoT() * REPLAY, a, b, ECHO_LEVEL, true));
        }
        out.sort((x, y) -> Double.compare(x.t(), y.t()));
        return out;
    }

    /** Phase from a call's spacing to the next event, split at {@link #SEARCH_SPLIT_S} and {@link #BUZZ_SPLIT_S}. */
    public static Phase phaseFromSpacing(double ipi) {
        if (ipi >= SEARCH_SPLIT_S) {
            return Phase.SEARCH;
        }
        return ipi <= BUZZ_SPLIT_S ? Phase.BUZZ : Phase.APPROACH;
    }

    /** Least-squares slope of naive range against call time gives the closing speed, then ranges are corrected. */
    public Reading solve() {
        int n = calls.size();
        double[] tt = new double[n];
        double[] r = new double[n];
        for (int i = 0; i < n; i++) {
            tt[i] = calls.get(i).t();
            r[i] = c * calls.get(i).delay() / 2;
        }
        double s = slope(tt, r);
        // naive r = d c / (c + v) and d falls at v, so s = -v c / (c + v), v = -s c / (c + s).
        double v = -s * c / (c + s);
        List<Double> ranges = new ArrayList<>();
        List<Phase> phases = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            ranges.add((c + v) * calls.get(i).delay() / 2);
            double next = i + 1 < n ? calls.get(i + 1).t() : catchT;
            phases.add(phaseFromSpacing(next - calls.get(i).t()));
        }
        return new Reading(v, ranges, phases);
    }

    static double slope(double[] x, double[] y) {
        int n = x.length;
        double mx = 0;
        double my = 0;
        for (int i = 0; i < n; i++) {
            mx += x[i];
            my += y[i];
        }
        mx /= n;
        my /= n;
        double sxy = 0;
        double sxx = 0;
        for (int i = 0; i < n; i++) {
            sxy += (x[i] - mx) * (y[i] - my);
            sxx += (x[i] - mx) * (x[i] - mx);
        }
        return sxy / sxx;
    }

    /**
     * Judge: one range guess per mark and one phase per call. Score = 50 x (ranges within tolerance / marks)
     * + 50 x (phases right / calls), rounded.
     */
    public Verdict judge(List<Double> markRanges, List<Phase> phases) {
        int rr = 0;
        for (int k = 0; k < marks.size() && k < markRanges.size(); k++) {
            Double g = markRanges.get(k);
            if (g != null && Math.abs(g - calls.get(marks.get(k)).rangeM()) <= TOLERANCE_M) {
                rr++;
            }
        }
        int pr = 0;
        for (int i = 0; i < calls.size() && i < phases.size(); i++) {
            if (phases.get(i) == calls.get(i).phase()) {
                pr++;
            }
        }
        int score = (int) Math.round(50.0 * rr / marks.size() + 50.0 * pr / calls.size());
        return new Verdict(rr, pr, score);
    }
}
