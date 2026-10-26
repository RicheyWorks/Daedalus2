// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.convoy;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * A split of the fleet into convoys (e.g. [3, 3] or [6]). The exact distribution of arks arriving is the convolution of
 * each convoy's storm / no-storm binomial mixture; {@link #simulate} checks it by seeded Monte Carlo.
 */
public final class ConvoyPlan {

    private final List<Integer> convoys;
    private final ConvoyRisk risk;

    public ConvoyPlan(List<Integer> convoys, ConvoyRisk risk) {
        this.risk = Objects.requireNonNull(risk, "risk");
        this.convoys = List.copyOf(Objects.requireNonNull(convoys, "convoys"));
        if (this.convoys.isEmpty()) {
            throw new IllegalArgumentException("need at least one convoy");
        }
        for (int c : this.convoys) {
            if (c < 1) {
                throw new IllegalArgumentException("convoy size must be >= 1: " + c);
            }
        }
    }

    public List<Integer> convoys() {
        return List.copyOf(convoys);
    }

    public int arks() {
        return convoys.stream().mapToInt(Integer::intValue).sum();
    }

    /** Exact P(arrive = a) for a = 0..arks. */
    public double[] arrivals() {
        double[] dist = {1.0};
        for (int c : convoys) {
            double[] one = new double[c + 1];
            addBinomial(one, c, 1 - risk.loss(c, false), 1 - risk.shock());
            addBinomial(one, c, 1 - risk.loss(c, true), risk.shock());
            dist = convolve(dist, one);
        }
        return dist;
    }

    /** Exact P(at least {@code k} arks arrive). */
    public double atLeast(int k) {
        double[] d = arrivals();
        double p = 0;
        for (int a = Math.max(0, k); a < d.length; a++) {
            p += d[a];
        }
        return p;
    }

    /** Exact expected arrivals. */
    public double expectedArrivals() {
        double[] d = arrivals();
        double e = 0;
        for (int a = 0; a < d.length; a++) {
            e += a * d[a];
        }
        return e;
    }

    /** One crossing on {@code rng}: arks that arrive. */
    public int sail(OddsRng rng) {
        int arrived = 0;
        for (int c : convoys) {
            boolean storm = rng.chance(risk.shock());
            double loss = risk.loss(c, storm);
            for (int i = 0; i < c; i++) {
                if (!rng.chance(loss)) {
                    arrived++;
                }
            }
        }
        return arrived;
    }

    /** Seeded estimate of P(at least {@code k}) with a 95% Wilson interval: {estimate, lo, hi}. */
    public double[] simulate(int k, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        int hits = 0;
        for (int t = 0; t < trials; t++) {
            if (sail(OddsRng.forTrial(seed, t)) >= k) {
                hits++;
            }
        }
        double[] ci = Intervals.wilson(hits, trials);
        return new double[] {hits / (double) trials, ci[0], ci[1]};
    }

    /** Every way to split {@code n} arks into convoys (non-increasing sizes), e.g. 4 -> [4], [3,1], [2,2], ... */
    public static List<List<Integer>> splits(int n) {
        if (n < 1 || n > 12) {
            throw new IllegalArgumentException("n must be in [1, 12]: " + n);
        }
        List<List<Integer>> out = new ArrayList<>();
        partition(n, n, new ArrayList<>(), out);
        return out;
    }

    private static void partition(int left, int max, List<Integer> cur, List<List<Integer>> out) {
        if (left == 0) {
            out.add(List.copyOf(cur));
            return;
        }
        for (int s = Math.min(left, max); s >= 1; s--) {
            cur.add(s);
            partition(left - s, s, cur, out);
            cur.remove(cur.size() - 1);
        }
    }

    private static void addBinomial(double[] into, int n, double p, double weight) {
        double q = 1 - p;
        double c = 1;
        for (int k = 0; k <= n; k++) {
            into[k] += weight * c * Math.pow(p, k) * Math.pow(q, n - k);
            c = c * (n - k) / (k + 1);
        }
    }

    private static double[] convolve(double[] a, double[] b) {
        double[] out = new double[a.length + b.length - 1];
        for (int i = 0; i < a.length; i++) {
            for (int j = 0; j < b.length; j++) {
                out[i + j] += a[i] * b[j];
            }
        }
        return out;
    }
}
