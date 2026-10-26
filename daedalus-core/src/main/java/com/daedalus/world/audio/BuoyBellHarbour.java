// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Buoy Bell Harbour (contest G72): the arks come home to a harbour that only opens when the bells agree.
 *
 * <p>2-4 seeded harbour buoys ring on their own beat cycles; the sea gate opens only on beats where every
 * buoy rings together ({@link BeatCoincidence}). 3-5 returning arks (names from
 * {@link FogBellCallSigns#ARKS}) each need a seeded number of beats to sail in. The player picks each ark's
 * departure beat (not before {@link #now()}) so every ark arrives on its own gate beat. The harbour master
 * judges against the shortest schedule: gate beats are taken in order and any ark that can reach a gate in
 * time may use it, so filling every gate greedily is optimal.
 *
 * <p>Ear rules: buoy bells at E4/G4/A4/C5 ({@link #buoyHz(int)}), gain {@link #GAIN}; beat
 * {@link #BEAT_MS} ms.
 */
public final class BuoyBellHarbour {
    /** Beat length, ms. */
    public static final int BEAT_MS = 400;
    /** Buoy gain. */
    public static final double GAIN = 0.3;
    private static final double[] BUOY_HZ = {329.628, 391.995, 440.0, 523.251};
    private static final long SALT = 0x4242_4831L; // "BBH1"

    /** One buoy. */
    public record Buoy(int period, int offset, double hz) { }

    /** One returning ark. */
    public record Ark(String name, int sailBeats) { }

    /** A judged schedule. */
    public record Verdict(boolean valid, boolean shortest, long lastArrival, long best, String reason) { }

    private final long seed;
    private final List<Buoy> buoys;
    private final List<Ark> arks;
    private final int now;
    private final int[] periods;
    private final int[] offsets;

    private BuoyBellHarbour(long seed, List<Buoy> buoys, List<Ark> arks, int now) {
        this.seed = seed;
        this.buoys = List.copyOf(buoys);
        this.arks = List.copyOf(arks);
        this.now = now;
        this.periods = new int[buoys.size()];
        this.offsets = new int[buoys.size()];
        for (int i = 0; i < periods.length; i++) {
            periods[i] = buoys.get(i).period();
            offsets[i] = buoys.get(i).offset();
        }
    }

    /** A seeded harbour evening. */
    public static BuoyBellHarbour seeded(long seed) {
        Rng rng = new Rng(seed ^ SALT);
        int nb = 2 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
        int hidden = (int) Long.remainderUnsigned(rng.nextLong(), 60);
        List<Integer> pool = new ArrayList<>(List.of(2, 3, 4, 5, 6));
        List<Buoy> buoys = new ArrayList<>();
        for (int i = 0; i < nb; i++) {
            int p = pool.remove((int) Long.remainderUnsigned(rng.nextLong(), pool.size()));
            buoys.add(new Buoy(p, hidden % p, BUOY_HZ[i]));
        }
        int na = 3 + (int) Long.remainderUnsigned(rng.nextLong(), 3);
        List<String> names = new ArrayList<>(FogBellCallSigns.ARKS);
        List<Ark> arks = new ArrayList<>();
        for (int i = 0; i < na; i++) {
            String name = names.remove((int) Long.remainderUnsigned(rng.nextLong(), names.size()));
            arks.add(new Ark(name, 3 + (int) Long.remainderUnsigned(rng.nextLong(), 38)));
        }
        int now = (int) Long.remainderUnsigned(rng.nextLong(), 21);
        return new BuoyBellHarbour(seed, buoys, arks, now);
    }

    /** Pitch of buoy {@code i}. */
    public static double buoyHz(int i) {
        return BUOY_HZ[i];
    }

    /** The seed. */
    public long seed() {
        return seed;
    }

    /** The buoys. */
    public List<Buoy> buoys() {
        return buoys;
    }

    /** The arks, in roster order. */
    public List<Ark> arks() {
        return arks;
    }

    /** Current beat; no ark may leave before it. */
    public int now() {
        return now;
    }

    /** True when the gate is open on {@code beat} (every buoy rings). */
    public boolean gateOpen(long beat) {
        return beat >= 0 && BeatCoincidence.next(periods, offsets, beat) == beat;
    }

    /** First gate beat at or after {@code beat}. */
    public long nextGate(long beat) {
        return BeatCoincidence.next(periods, offsets, Math.max(0, beat));
    }

    /** Shortest schedule: departure beat per ark (roster order). */
    public List<Long> solution() {
        long[] dep = new long[arks.size()];
        boolean[] done = new boolean[arks.size()];
        int left = arks.size();
        long gate = nextGate(now);
        while (left > 0) {
            int pick = -1;
            for (int i = 0; i < arks.size(); i++) {
                int d = arks.get(i).sailBeats();
                if (!done[i] && gate - d >= now && (pick < 0 || d > arks.get(pick).sailBeats())) {
                    pick = i;
                }
            }
            if (pick >= 0) {
                done[pick] = true;
                dep[pick] = gate - arks.get(pick).sailBeats();
                left--;
            }
            gate = nextGate(gate + 1);
        }
        List<Long> out = new ArrayList<>();
        for (long d : dep) {
            out.add(d);
        }
        return out;
    }

    /** Last arrival of the shortest schedule. */
    public long best() {
        long last = 0;
        List<Long> s = solution();
        for (int i = 0; i < s.size(); i++) {
            last = Math.max(last, s.get(i) + arks.get(i).sailBeats());
        }
        return last;
    }

    /** Judge departure beats (roster order). */
    public Verdict judge(List<Long> departures) {
        long best = best();
        if (departures == null || departures.size() != arks.size()) {
            return new Verdict(false, false, 0, best, "need a departure for each of " + arks.size() + " arks");
        }
        Set<Long> used = new HashSet<>();
        long last = 0;
        for (int i = 0; i < arks.size(); i++) {
            Ark a = arks.get(i);
            long dep = departures.get(i);
            if (dep < now) {
                return new Verdict(false, false, 0, best, a.name() + " cannot leave before beat " + now);
            }
            long arr = dep + a.sailBeats();
            if (!gateOpen(arr)) {
                return new Verdict(false, false, 0, best, a.name() + " reaches a shut gate at beat " + arr);
            }
            if (!used.add(arr)) {
                return new Verdict(false, false, 0, best, a.name() + " collides at the gate on beat " + arr);
            }
            last = Math.max(last, arr);
        }
        return new Verdict(true, last == best, last, best, last == best ? "harbour full by nightfall" : "safe, but slower");
    }
}