// SPDX-License-Identifier: MIT
//
// Harness for ADR-002 — "CSRBT RankedSet behind TailLatencyPowerOfTwoStrategy".
//
// Deliberately NOT part of the Maven reactor: it compiles against jars from two sibling
// projects (LoadBalancerPro and CSRBT), so wiring it into the build would couple this repo's
// CI to their local state. See ADR-002 "Reproducing" for the exact commands.
//
// What it measures: four routing policies against a simulated heterogeneous fleet, swept over
// how stale the balancer's view of that fleet is. Staleness is the variable that decides the
// question — a benchmark that hands the strategy a perfectly fresh view is measuring a system
// nobody runs, and will flatter greedy selection.

import com.richmond423.loadbalancerpro.core.*;
import io.github.richeyworks.csrbt.OrderedSet;
import io.github.richeyworks.csrbt.strategy.RedBlackStrategy;

import java.time.Clock;
import java.time.Instant;
import java.util.*;

/** ADR-001 item 7: is a CSRBT RankedSet worth putting behind TailLatencyPowerOfTwoStrategy? */
public class CsrbtRoutingEval {

    static final int WARM = 2000;
    static final ServerScoreCalculator SCORER = new ServerScoreCalculator();

    /** Mutable fleet state the simulation advances; snapshotted into ServerStateVectors. */
    static final class Fleet {
        final int n; final double[] capacity; final int[] inFlight;
        final double[] ewmaP95, ewmaP99, ewmaAvg;
        Fleet(int n, Random r) {
            this.n = n; capacity = new double[n]; inFlight = new int[n];
            ewmaP95 = new double[n]; ewmaP99 = new double[n]; ewmaAvg = new double[n];
            for (int i = 0; i < n; i++) {
                capacity[i] = 4 + r.nextInt(28);          // heterogeneous fleet
                ewmaP95[i] = 10; ewmaP99[i] = 12; ewmaAvg[i] = 8;
            }
        }
        /** Latency a request would see landing on i right now. */
        double latency(int i) { return 5.0 * (1 + inFlight[i]) / capacity[i]; }
        void observe(int i, double lat) {
            ewmaAvg[i] = 0.9 * ewmaAvg[i] + 0.1 * lat;
            ewmaP95[i] = 0.9 * ewmaP95[i] + 0.1 * lat * 1.4;
            ewmaP99[i] = 0.9 * ewmaP99[i] + 0.1 * lat * 1.8;
        }
        List<ServerStateVector> snapshot(Instant t) {
            List<ServerStateVector> out = new ArrayList<>(n);
            for (int i = 0; i < n; i++)
                out.add(new ServerStateVector("s" + i, true, inFlight[i], capacity[i], capacity[i],
                        ewmaAvg[i], ewmaP95[i], ewmaP99[i], 0.0, 0, t));
            return out;
        }
    }

    interface Chooser { int pick(List<ServerStateVector> s, Random r); }

    static int idOf(ServerStateVector v) { return Integer.parseInt(v.serverId().substring(1)); }

    /** The shipped strategy: uniform sample of 2, lower score wins. */
    static Chooser uniformPo2() {
        return (s, r) -> {
            int i = r.nextInt(s.size()), j = r.nextInt(s.size() - 1);
            if (j >= i) j++;
            return SCORER.score(s.get(i)) <= SCORER.score(s.get(j)) ? idOf(s.get(i)) : idOf(s.get(j));
        };
    }

    /** Greedy least-score — the herding baseline. */
    static Chooser greedy() {
        return (s, r) -> {
            int best = 0; double bs = Double.MAX_VALUE;
            for (int k = 0; k < s.size(); k++) {
                double sc = SCORER.score(s.get(k));
                if (sc < bs) { bs = sc; best = k; }
            }
            return idOf(s.get(best));
        };
    }

    /** The proposal under evaluation: CSRBT RankedSet gates to the best pct%, then po2 inside it. */
    static Chooser rankedGatedPo2(int pct) {
        return (s, r) -> {
            OrderedSet<Double> tree = OrderedSet.<Double>withNaturalOrder(new RedBlackStrategy<Double>());
            double[] sc = new double[s.size()];
            for (int k = 0; k < s.size(); k++) { sc[k] = SCORER.score(s.get(k)); tree.add(sc[k]); }
            Double cut = tree.percentile(pct);
            double threshold = cut == null ? Double.MAX_VALUE : cut;
            List<Integer> pool = new ArrayList<>();
            for (int k = 0; k < s.size(); k++) if (sc[k] <= threshold) pool.add(k);
            if (pool.isEmpty()) return idOf(s.get(0));
            if (pool.size() == 1) return idOf(s.get(pool.get(0)));
            int i = r.nextInt(pool.size()), j = r.nextInt(pool.size() - 1);
            if (j >= i) j++;
            int a = pool.get(i), b = pool.get(j);
            return sc[a] <= sc[b] ? idOf(s.get(a)) : idOf(s.get(b));
        };
    }

    /**
     * Each arrival is one tick. A request occupies its server for a service duration that
     * scales inversely with capacity; the latency it observes also pays for whatever was
     * already in flight there. SERVICE sets the offered load — 320 ticks against 64 servers
     * at one arrival per tick means ~5 concurrent requests per server, i.e. real contention.
     */
    static final int SERVICE = 320;

    /** Same gating policy, but the threshold comes from an O(n) partial select, no tree. */
    static Chooser quickselectGatedPo2(int pct) {
        return (s, r) -> {
            int m = s.size();
            double[] sc = new double[m];
            for (int k = 0; k < m; k++) sc[k] = SCORER.score(s.get(k));
            double[] copy = sc.clone();
            int idx = Math.max(0, Math.min(m - 1, (int) Math.ceil(pct / 100.0 * m) - 1));
            double threshold = select(copy, 0, m - 1, idx);
            List<Integer> pool = new ArrayList<>();
            for (int k = 0; k < m; k++) if (sc[k] <= threshold) pool.add(k);
            if (pool.isEmpty()) return idOf(s.get(0));
            if (pool.size() == 1) return idOf(s.get(pool.get(0)));
            int i = r.nextInt(pool.size()), j = r.nextInt(pool.size() - 1);
            if (j >= i) j++;
            int x = pool.get(i), y = pool.get(j);
            return sc[x] <= sc[y] ? idOf(s.get(x)) : idOf(s.get(y));
        };
    }

    /** Hoare partial selection — average O(n). */
    static double select(double[] v, int lo, int hi, int k) {
        while (lo < hi) {
            double pivot = v[(lo + hi) >>> 1];
            int i = lo, j = hi;
            while (i <= j) {
                while (v[i] < pivot) i++;
                while (v[j] > pivot) j--;
                if (i <= j) { double t = v[i]; v[i] = v[j]; v[j] = t; i++; j--; }
            }
            if (k <= j) hi = j; else if (k >= i) lo = i; else return v[k];
        }
        return v[lo];
    }

    static double[] run(Chooser c, int n, int requests, long seed, int stale) {
        Random r = new Random(seed);
        Fleet f = new Fleet(n, new Random(seed));
        Instant t = Instant.now();
        double capAvg = Arrays.stream(f.capacity).average().orElse(1);
        double[] lat = new double[requests];
        int maxInFlight = 0;
        long decisionNanos = 0;
        List<ServerStateVector> cached = null;
        PriorityQueue<long[]> completions = new PriorityQueue<>((x, y) -> Long.compare(x[0], y[0]));

        for (int q = 0; q < requests; q++) {
            while (!completions.isEmpty() && completions.peek()[0] <= q) {
                f.inFlight[(int) completions.poll()[1]]--;
            }
            // A real balancer routes on a view that is already out of date: health checks
            // and metric scrapes land on an interval, and with several balancer replicas they
            // all act on the same stale picture. That delay is the entire reason
            // power-of-two-choices exists, so a benchmark without it flatters greedy.
            if (q % Math.max(1, stale) == 0) cached = f.snapshot(t);
            List<ServerStateVector> snap = cached == null ? f.snapshot(t) : cached;
            long t0 = System.nanoTime();
            int pick = c.pick(snap, r);
            decisionNanos += System.nanoTime() - t0;

            double service = SERVICE * capAvg / f.capacity[pick] / n;
            double observed = service * (1 + f.inFlight[pick]);
            f.inFlight[pick]++;
            f.observe(pick, observed);
            completions.add(new long[]{q + Math.max(1, Math.round(service * n / capAvg * f.capacity[pick] / capAvg)), pick});
            lat[q] = observed;
            for (int v : f.inFlight) maxInFlight = Math.max(maxInFlight, v);
        }
        double[] tail = Arrays.copyOfRange(lat, WARM, requests);
        Arrays.sort(tail);
        return new double[]{Arrays.stream(tail).average().orElse(0),
                tail[(int) (tail.length * 0.99)], maxInFlight,
                decisionNanos / (double) requests};
    }

    public static void main(String[] a) {
        int n = 64, requests = 40000;
        System.out.printf("fleet=%d servers, %d requests, po2 gate=best 20%%%n", n, requests);
        for (int stale : new int[]{1, 25, 100}) {
            System.out.printf("%n--- balancer view refreshed every %d requests ---%n", stale);
            System.out.printf("%-26s %9s %9s %11s %12s%n",
                    "strategy", "mean ms", "p99 ms", "max inflt", "ns/decision");
            record Row(String name, Chooser c) {}
            for (Row row : List.of(
                    new Row("uniform po2 (shipped)", uniformPo2()),
                    new Row("greedy least-score", greedy()),
                    new Row("RankedSet-gated po2", rankedGatedPo2(20)),
                    new Row("quickselect-gated po2", quickselectGatedPo2(20)))) {
                double[] m = run(row.c(), n, requests, 1L, stale);
                System.out.printf("%-26s %9.2f %9.2f %11.0f %12.0f%n",
                        row.name(), m[0], m[1], m[2], m[3]);
            }
        }
    }
}
