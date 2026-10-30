// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class BuoyBellHarbourTest {
    @Test void solutionIsValidAndShortest() {
        for (long s = 0; s < 200; s++) {
            BuoyBellHarbour h = BuoyBellHarbour.seeded(s);
            assertThat(h.buoys().size()).isBetween(2, 4);
            assertThat(h.arks().size()).isBetween(3, 5);
            BuoyBellHarbour.Verdict v = h.judge(h.solution());
            assertThat(v.valid()).as("seed %d %s", s, v.reason()).isTrue();
            assertThat(v.shortest()).isTrue();
            assertThat(v.best()).as("seed %d", s).isEqualTo(bruteBest(h));
            assertThat(h.seed()).isEqualTo(s);
        }
    }

    /** Every ark order, each ark taking the earliest free gate it can reach: the best over orders is optimal. */
    private static long bruteBest(BuoyBellHarbour h) {
        int n = h.arks().size();
        long best = Long.MAX_VALUE;
        for (List<Integer> order : perms(n)) {
            Set<Long> used = new HashSet<>();
            long last = 0;
            for (int i : order) {
                long g = h.nextGate(h.now() + h.arks().get(i).sailBeats());
                while (used.contains(g)) {
                    g = h.nextGate(g + 1);
                }
                used.add(g);
                last = Math.max(last, g);
            }
            best = Math.min(best, last);
        }
        return best;
    }

    private static List<List<Integer>> perms(int n) {
        List<List<Integer>> out = new ArrayList<>();
        if (n == 0) {
            out.add(new ArrayList<>());
            return out;
        }
        for (List<Integer> p : perms(n - 1)) {
            for (int k = 0; k <= p.size(); k++) {
                List<Integer> q = new ArrayList<>(p);
                q.add(k, n - 1);
                out.add(q);
            }
        }
        return out;
    }

    @Test void gateMatchesEveryBuoyRinging() {
        BuoyBellHarbour h = BuoyBellHarbour.seeded(9);
        for (long b = 0; b < 120; b++) {
            boolean all = true;
            for (BuoyBellHarbour.Buoy y : h.buoys()) {
                all &= b % y.period() == y.offset();
            }
            assertThat(h.gateOpen(b)).isEqualTo(all);
        }
        assertThat(h.gateOpen(-1)).isFalse();
        assertThat(BuoyBellHarbour.buoyHz(2)).isEqualTo(440.0);
    }

    @Test void judgeRejectsBadSchedules() {
        BuoyBellHarbour h = BuoyBellHarbour.seeded(4);
        List<Long> sol = h.solution();
        assertThat(h.judge(null).reason()).startsWith("need");
        List<Long> early = new ArrayList<>(sol);
        early.set(0, (long) h.now() - 1);
        assertThat(h.judge(early).reason()).contains("cannot leave");
        List<Long> shut = new ArrayList<>(sol);
        shut.set(0, sol.get(0) + 1);
        assertThat(h.judge(shut).valid()).isFalse();
        List<Long> clash = new ArrayList<>(sol);
        clash.set(1, sol.get(0) + h.arks().get(0).sailBeats() - h.arks().get(1).sailBeats());
        if (clash.get(1) >= h.now()) {
            assertThat(h.judge(clash).reason()).contains("collides");
        }
        long period = BeatCoincidence.lcm(h.buoys().stream().mapToInt(BuoyBellHarbour.Buoy::period).toArray());
        List<Long> slow = new ArrayList<>(sol);
        int lastArk = 0;
        for (int i = 0; i < sol.size(); i++) {
            if (sol.get(i) + h.arks().get(i).sailBeats() > sol.get(lastArk) + h.arks().get(lastArk).sailBeats()) {
                lastArk = i;
            }
        }
        slow.set(lastArk, sol.get(lastArk) + period);
        BuoyBellHarbour.Verdict v = h.judge(slow);
        assertThat(v.valid()).isTrue();
        assertThat(v.shortest()).isFalse();
        assertThat(v.reason()).isEqualTo("safe, but slower");
    }
}