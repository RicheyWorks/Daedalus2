// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import com.daedalus.world.battlefield.BattlefieldEcology.EventKind;

/**
 * Latency benchmark (ADR-061): median and p99 of tick, bestCover, concealmentBetween and a DBE 1 write/read on a
 * burning grid. Usage: {@code BattlefieldBench [size] [iterations]}.
 */
public final class BattlefieldBench {

    private BattlefieldBench() {
    }

    /** Median and p99 in microseconds. */
    public record Stat(String name, double medianUs, double p99Us) {
        @Override
        public String toString() {
            return String.format("%-22s median %9.1f us   p99 %9.1f us", name, medianUs, p99Us);
        }
    }

    /** Runs the benchmark and returns one stat per operation. */
    public static Stat[] run(int n, int iterations) {
        BattlefieldEcology e = new BattlefieldEcology(n, n, 100, 0, 0, 7).wind(0.5, 0.2);
        Vegetation[] mix = {Vegetation.MEADOW, Vegetation.SCRUB, Vegetation.PINE, Vegetation.OAK};
        for (int j = 0; j < n; j++) {
            for (int i = 0; i < n; i++) {
                e.set(i, j, mix[(i / 7 + j / 5) % mix.length]);
            }
        }
        double mid = n * 50.0;
        e.apply(EventKind.IGNITE, mid, mid, 600);
        long[][] t = new long[4][iterations];
        for (int k = 0; k < iterations; k++) {
            long a = System.nanoTime();
            e.tick();
            long b = System.nanoTime();
            e.bestCover(mid - 1500, mid, mid + 3000, mid, 1500);
            long c = System.nanoTime();
            e.concealmentBetween(100, 100, n * 100.0 - 100, n * 100.0 - 100);
            long d = System.nanoTime();
            Dbe.read(Dbe.write(e));
            long f = System.nanoTime();
            t[0][k] = b - a;
            t[1][k] = c - b;
            t[2][k] = d - c;
            t[3][k] = f - d;
        }
        String[] names = {"tick", "bestCover r=15m", "concealmentBetween", "DBE write+read"};
        Stat[] out = new Stat[4];
        for (int s = 0; s < 4; s++) {
            long[] v = t[s].clone();
            java.util.Arrays.sort(v);
            out[s] = new Stat(names[s], v[v.length / 2] / 1e3, v[Math.min(v.length - 1, (int) (v.length * 0.99))] / 1e3);
        }
        return out;
    }

    /** Entry point. */
    public static void main(String[] args) {
        int n = args.length > 0 ? Integer.parseInt(args[0]) : 256;
        int it = args.length > 1 ? Integer.parseInt(args[1]) : 300;
        run(n, Math.max(20, it / 5));
        System.out.println("grid " + n + "x" + n + ", " + it + " iterations");
        for (Stat s : run(n, it)) {
            System.out.println(s);
        }
    }
}