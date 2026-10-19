// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.world.audio.Rng;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * LAB03 Echo Bell timing gate: "listen to the maze before trusting a map".
 *
 * <p>A seeded peal of soft bells rings; each bell's echo comes back after a delay set by how deep
 * the corridor behind it runs (host passes real maze depths, e.g. from a solver or ChalkTrail route,
 * or the seed picks them). The gate opens only if the player taps once per echo, in order, inside
 * the timing window. A miss resets the puzzle (same seed, same peal), never realm progress.
 *
 * <p>Ear rules: bells use a low D minor pentatonic (146.8-349.2 Hz), no bright or piercing tones;
 * bells that follow quickly (passing notes) ring at half gain. Pure data: playback is the host's.
 * Generation uses only integer math plus one pow per bell, so the C++ core
 * {@code DaedalusEchoBellCore.h} reproduces it exactly (fixture {@code docs/contracts/echo-bell-v1}).
 */
public final class EchoBellGate {
    /** Lowest bell, D3. */
    public static final double ROOT_HZ = 146.832;
    /** Highest frequency any bell may use (ear rule). */
    public static final double MAX_HZ = 360.0;
    private static final int[] PENTATONIC = {0, 3, 5, 7, 10};
    private static final long SALT = 0x4542_4731L; // "EBG1"

    /** One bell strike and its echo, times in ms from the start of the peal. */
    public record Ring(int index, int ringMs, double hz, double gain, int depthCells, int echoMs) { }

    /** Outcome of one attempt. offsetsMs[i] = tap minus echo for matched taps. */
    public record Verdict(boolean open, int hits, int firstMiss, List<Integer> offsetsMs) {
        /** Defensive copy. */
        public Verdict {
            offsetsMs = List.copyOf(offsetsMs);
        }
    }

    private final long seed;
    private final int difficulty;
    private final boolean crickets;
    private final List<Ring> rings;
    private final int windowMs;

    private EchoBellGate(long seed, int difficulty, boolean crickets, int[] depths) {
        if (difficulty < 0 || difficulty > 3) {
            throw new IllegalArgumentException("difficulty 0-3");
        }
        int n = 3 + difficulty;
        if (depths != null && depths.length != n) {
            throw new IllegalArgumentException("need one corridor depth per bell: " + n);
        }
        this.seed = seed;
        this.difficulty = difficulty;
        this.crickets = crickets;
        Rng rng = new Rng(seed ^ SALT);
        List<Ring> out = new ArrayList<>();
        int t = 0;
        for (int i = 0; i < n; i++) {
            int degree = PENTATONIC[(int) Long.remainderUnsigned(rng.nextLong(), PENTATONIC.length)];
            int octave = (int) Long.remainderUnsigned(rng.nextLong(), 2);
            int semis = degree + 12 * octave;
            if (semis > 15) {
                semis -= 12; // ear rule: never above F4
            }
            int gap = 600 + 150 * (int) Long.remainderUnsigned(rng.nextLong(), 5);
            int rolledDepth = 2 + (int) Long.remainderUnsigned(rng.nextLong(), 9);
            int depth = depths == null ? rolledDepth : depths[i];
            if (depth < 1 || depth > 40) {
                throw new IllegalArgumentException("corridor depth 1-40 cells");
            }
            t += gap;
            double hz = Math.round(ROOT_HZ * Math.pow(2.0, semis / 12.0) * 1000.0) / 1000.0;
            double gain = gap <= 750 ? 0.3 : 0.6; // passing notes stay light
            out.add(new Ring(i, t, hz, gain, depth, t + echoDelayMs(depth)));
        }
        this.rings = List.copyOf(out);
        int base = 140 - 20 * difficulty;
        this.windowMs = crickets ? base * 3 / 2 : base;
    }

    /** Seed picks the corridor depths. Echo Crickets (assist) widen the window by half. */
    public static EchoBellGate seeded(long seed, int difficulty, boolean crickets) {
        return new EchoBellGate(seed, difficulty, crickets, null);
    }

    /** Host passes real corridor depths (cells) from the generated maze, one per bell. */
    public static EchoBellGate fromMazeDepths(long seed, int difficulty, boolean crickets, int[] depths) {
        if (depths == null) {
            throw new IllegalArgumentException("depths required");
        }
        return new EchoBellGate(seed, difficulty, crickets, depths.clone());
    }

    /** Gameplay-scaled echo: 200 ms plus 70 ms per corridor cell. */
    public static int echoDelayMs(int depthCells) {
        return 200 + 70 * depthCells;
    }

    /** The peal in ring order. */
    public List<Ring> rings() {
        return rings;
    }

    /** Half-width of the tap window in ms. */
    public int windowMs() {
        return windowMs;
    }

    /** Judges one attempt: exactly one tap per echo, ascending, each within the window. */
    public Verdict judge(List<Integer> tapsMs) {
        if (tapsMs == null) {
            throw new IllegalArgumentException("taps required");
        }
        List<Integer> echoes = new ArrayList<>();
        for (Ring r : rings) {
            echoes.add(r.echoMs());
        }
        echoes.sort(null);
        List<Integer> offsets = new ArrayList<>();
        int hits = 0;
        int firstMiss = -1;
        for (int i = 0; i < echoes.size(); i++) {
            if (i >= tapsMs.size() || tapsMs.get(i) == null || (i > 0 && tapsMs.get(i - 1) != null
                    && tapsMs.get(i) < tapsMs.get(i - 1))) {
                firstMiss = firstMiss < 0 ? i : firstMiss;
                continue;
            }
            int off = tapsMs.get(i) - echoes.get(i);
            offsets.add(off);
            if (Math.abs(off) <= windowMs) {
                hits++;
            } else if (firstMiss < 0) {
                firstMiss = i;
            }
        }
        boolean open = hits == echoes.size() && tapsMs.size() == echoes.size();
        if (!open && firstMiss < 0) {
            firstMiss = echoes.size(); // extra tap
        }
        return new Verdict(open, hits, open ? -1 : firstMiss, offsets);
    }

    /** A fresh attempt after a miss: same seed and settings, so the player can learn the peal. */
    public EchoBellGate retry() {
        int[] depths = rings.stream().mapToInt(Ring::depthCells).toArray();
        return new EchoBellGate(seed, difficulty, crickets, depths);
    }

    /** EBG 1 text form used by the C++ parity fixture. */
    public String toWire() {
        StringBuilder sb = new StringBuilder("EBG 1\n");
        sb.append(String.format(Locale.ROOT, "gate %d %d %d %d%n", seed, difficulty, crickets ? 1 : 0, windowMs)
                .replace(System.lineSeparator(), "\n"));
        for (Ring r : rings) {
            sb.append(String.format(Locale.ROOT, "bell %d %d %.3f %.3f %d %d", r.index(), r.ringMs(), r.hz(), r.gain(),
                    r.depthCells(), r.echoMs())).append('\n');
        }
        return sb.append("end\n").toString();
    }
}