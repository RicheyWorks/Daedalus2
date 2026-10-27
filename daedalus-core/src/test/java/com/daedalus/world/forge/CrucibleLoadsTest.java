// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.CrucibleLoads.Firing;
import com.daedalus.world.forge.CrucibleLoads.Grade;
import com.daedalus.world.forge.CrucibleLoads.Haul;
import com.daedalus.world.forge.CrucibleLoads.Rule;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CrucibleLoadsTest {

    /** Brute force: try every assignment of lumps to crucibles (restricted growth strings). */
    private static int bruteForce(int[] w, int cap) {
        if (w.length == 0) {
            return 0;
        }
        return brute(w, cap, 0, new int[w.length], 0, w.length);
    }

    private static int brute(int[] w, int cap, int i, int[] load, int open, int best) {
        if (i == w.length) {
            return Math.min(best, open);
        }
        for (int b = 0; b <= open && b < w.length; b++) {
            if (load[b] + w[i] <= cap) {
                load[b] += w[i];
                best = brute(w, cap, i + 1, load, Math.max(open, b + 1), best);
                load[b] -= w[i];
            }
        }
        return best;
    }

    private static void assertValid(int[] w, int cap, List<List<Integer>> bins) {
        Set<Integer> seen = new HashSet<>();
        for (List<Integer> bin : bins) {
            assertThat(bin).isNotEmpty();
            int sum = 0;
            for (int i : bin) {
                assertThat(seen.add(i)).isTrue();
                sum += w[i];
            }
            assertThat(sum).isLessThanOrEqualTo(cap);
        }
        assertThat(seen).hasSize(w.length);
    }

    @Test
    void exactSolverMatchesBruteForceOnSeededHauls() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = 1 + (int) (seed % 9);
            int cap = 5 + (int) (seed % 17);
            int[] w = CrucibleLoads.haul(seed, n, cap).weights();
            assertThat(CrucibleLoads.optimal(w, cap)).as("seed %d", seed).isEqualTo(bruteForce(w, cap));
        }
    }

    @Test
    void everyRulePacksValidlyAndNeverBeatsTheOptimum() {
        for (long seed = 1; seed <= 200; seed++) {
            Haul h = CrucibleLoads.haul(seed, 4 + (int) (seed % 14), 10 + (int) (seed % 40));
            int[] w = h.weights();
            int opt = CrucibleLoads.optimal(w, h.capacity());
            assertThat(opt).isGreaterThanOrEqualTo(h.lowerBound());
            for (Rule r : Rule.values()) {
                List<List<Integer>> bins = CrucibleLoads.pack(w, h.capacity(), r);
                assertValid(w, h.capacity(), bins);
                assertThat(bins.size()).isGreaterThanOrEqualTo(opt);
            }
        }
    }

    @Test
    void classicWorstCaseBoundsHold() {
        for (long seed = 1; seed <= 200; seed++) {
            Haul h = CrucibleLoads.haul(seed * 7919L, 6 + (int) (seed % 12), 20);
            int[] w = h.weights();
            int opt = CrucibleLoads.optimal(w, 20);
            int ffd = CrucibleLoads.pack(w, 20, Rule.FIRST_FIT_DECREASING).size();
            int nf = CrucibleLoads.pack(w, 20, Rule.NEXT_FIT).size();
            assertThat(9 * ffd).isLessThanOrEqualTo(11 * opt + 6);
            assertThat(nf).isLessThanOrEqualTo(2 * opt - 1);
        }
    }

    @Test
    void heaviestFirstBeatsArrivalOrderOnTheForgemastersExample() {
        int[] w = {3, 3, 3, 3, 7, 7, 7, 7};
        assertThat(CrucibleLoads.pack(w, 10, Rule.FIRST_FIT)).hasSize(5);
        assertThat(CrucibleLoads.pack(w, 10, Rule.FIRST_FIT_DECREASING)).hasSize(4);
        assertThat(CrucibleLoads.optimal(w, 10)).isEqualTo(4);
        assertThat(CrucibleLoads.pack(new int[] {6, 6, 5, 5}, 11, Rule.NEXT_FIT)).hasSize(3);
        assertThat(CrucibleLoads.optimal(new int[] {6, 6, 5, 5}, 11)).isEqualTo(2);
    }

    @Test
    void sameSeedReplaysTheSameFiring() {
        Haul a = CrucibleLoads.haul(189L, 14, 30);
        Haul b = CrucibleLoads.haul(189L, 14, 30);
        assertThat(a).isEqualTo(b);
        for (Rule r : Rule.values()) {
            assertThat(CrucibleLoads.fire(a, r)).isEqualTo(CrucibleLoads.fire(b, r));
        }
        assertThat(CrucibleLoads.haul(190L, 14, 30)).isNotEqualTo(a);
    }

    @Test
    void gradesAndLines() {
        assertThat(CrucibleLoads.grade(4, 4)).isEqualTo(Grade.WARM);
        assertThat(CrucibleLoads.grade(5, 4)).isEqualTo(Grade.SMOKY);
        assertThat(CrucibleLoads.grade(6, 4)).isEqualTo(Grade.WASTEFUL);
        assertThatThrownBy(() -> CrucibleLoads.grade(3, 4)).isInstanceOf(IllegalArgumentException.class);
        Haul h = new Haul(10, List.of(3, 3, 3, 3, 7, 7, 7, 7));
        Firing ff = CrucibleLoads.fire(h, Rule.FIRST_FIT);
        Firing ffd = CrucibleLoads.fire(h, Rule.FIRST_FIT_DECREASING);
        assertThat(ff.grade()).isEqualTo(Grade.SMOKY);
        assertThat(ffd.grade()).isEqualTo(Grade.WARM);
        assertThat(CrucibleLoads.forgemasterLine(ffd)).contains("4 crucibles");
        assertThat(CrucibleLoads.QUEST_ID).isEqualTo("q_crucible_loads");
    }

    @Test
    void edgeCasesAndRejects() {
        assertThat(CrucibleLoads.optimal(new int[0], 5)).isZero();
        assertThat(CrucibleLoads.pack(new int[0], 5, Rule.FIRST_FIT)).isEmpty();
        assertThat(CrucibleLoads.optimal(new int[] {5, 5, 5}, 5)).isEqualTo(3);
        assertThatThrownBy(() -> CrucibleLoads.pack(new int[] {6}, 5, Rule.NEXT_FIT))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Haul(0, List.of())).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrucibleLoads.optimal(new int[25], 5)).isInstanceOf(IllegalArgumentException.class);
        List<Integer> big = new ArrayList<>();
        for (int i = 0; i < 24; i++) {
            big.add(1 + (i * 37) % 50);
        }
        Haul h = new Haul(60, big);
        assertThat(CrucibleLoads.fire(h, Rule.FIRST_FIT_DECREASING).fewest()).isGreaterThanOrEqualTo(h.lowerBound());
    }
}
