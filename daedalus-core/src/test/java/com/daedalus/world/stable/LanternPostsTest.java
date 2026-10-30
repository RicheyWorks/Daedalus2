// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.LanternPosts.Plan;

import org.junit.jupiter.api.Test;

class LanternPostsTest {

    @Test
    void bestMatchesBruteForceOverEveryPathOwner() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = 1 + (int) (seed % 10);
            int reach = 1 + (int) (seed % 3);
            int[] parent = LanternPosts.yard(seed, n);
            int[] price = LanternPosts.prices(seed, n, 9);
            Plan b = LanternPosts.best(parent, price, reach);
            assertThat(b.cost()).as("seed %d", seed).isEqualTo(brute(parent, price, reach));
            if (b.cost() != LanternPosts.INFEASIBLE) {
                assertThat(LanternPosts.light(parent, price, reach, b.lighter())).isEqualTo(b.cost());
                assertThat(LanternPosts.quest(parent, price, reach, b.lighter())).isTrue();
            }
        }
    }

    @Test
    void busiestFirstIsNeverBetterAndUsuallyDearer() {
        // Ten junctions, prices 1-9, reach 2: the habit paid more on 217 of these 300 seeds when this was written.
        int dearer = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] parent = LanternPosts.yard(seed, 10);
            int[] price = LanternPosts.prices(seed, 10, 9);
            Plan b = LanternPosts.best(parent, price, 2);
            Plan g = LanternPosts.busiestFirst(parent, price, 2);
            assertThat(b.cost()).isNotEqualTo(LanternPosts.INFEASIBLE);
            if (g.cost() == LanternPosts.INFEASIBLE) {
                dearer++;
                continue;
            }
            assertThat(LanternPosts.light(parent, price, 2, g.lighter())).isEqualTo(g.cost());
            assertThat(g.cost()).isGreaterThanOrEqualTo(b.cost());
            if (g.cost() > b.cost()) {
                dearer++;
            }
        }
        assertThat(dearer).isGreaterThan(150);
    }

    @Test
    void cheapLeafLanternLeadsTheHabitAstray() {
        // Barn door (price 3) has paths to junction 1 (price 4) and junction 2 (price 1). Per coin the
        // leaf at 2 looks best, then the barn still has to be lit: 4. One barn lantern lights both: 3.
        int[] parent = {-1, 0, 0};
        int[] price = {3, 4, 1};
        Plan g = LanternPosts.busiestFirst(parent, price, 2);
        assertThat(g).isEqualTo(new Plan(4, new int[] {-1, 0, 2}));
        assertThat(LanternPosts.best(parent, price, 2)).isEqualTo(new Plan(3, new int[] {-1, 0, 0}));
        assertThat(LanternPosts.quest(parent, price, 2, g.lighter())).isFalse();
        // With reach 1 the barn cannot light both: cheapest is barn + leaf 2.
        assertThat(LanternPosts.best(parent, price, 1).cost()).isEqualTo(4);
    }

    @Test
    void darkOrOverloadedPlansAreInfeasible() {
        int[] parent = {-1, 0, 0, 0};
        int[] price = {1, 1, 1, 1};
        assertThat(LanternPosts.light(parent, price, 2, new int[] {-1, 0, 0, 3})).isEqualTo(2);
        assertThat(LanternPosts.light(parent, price, 2, new int[] {-1, 0, 0, 0})).isEqualTo(LanternPosts.INFEASIBLE);
        assertThat(LanternPosts.light(parent, price, 2, new int[] {-1, 2, 0, 3})).isEqualTo(LanternPosts.INFEASIBLE);
        assertThat(LanternPosts.light(parent, price, 2, new int[] {-1, 0})).isEqualTo(LanternPosts.INFEASIBLE);
        assertThat(LanternPosts.best(parent, price, 0).cost()).isEqualTo(LanternPosts.INFEASIBLE);
        assertThat(LanternPosts.busiestFirst(parent, price, 0).cost()).isEqualTo(LanternPosts.INFEASIBLE);
        assertThat(LanternPosts.best(new int[] {-1}, new int[] {5}, 0).cost()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(LanternPosts.yard(8, 9)).containsExactly(LanternPosts.yard(8, 9));
        assertThat(LanternPosts.prices(8, 9, 5)).containsExactly(LanternPosts.prices(8, 9, 5));
        assertThat(LanternPosts.QUEST_ID).isEqualTo("q_paths_lit");
        assertThatThrownBy(() -> LanternPosts.yard(1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LanternPosts.best(new int[] {-1, 1}, new int[] {1, 1}, 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LanternPosts.best(new int[] {-1}, new int[] {0}, 1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    /** Every way to give each path one of its two junctions; lanterns go wherever a path was given. */
    private static int brute(int[] parent, int[] price, int reach) {
        int n = parent.length;
        int edges = n - 1;
        int best = LanternPosts.INFEASIBLE;
        for (int mask = 0; mask < (1 << edges); mask++) {
            int[] lighter = new int[n];
            lighter[0] = -1;
            for (int e = 1; e < n; e++) {
                lighter[e] = ((mask >> (e - 1)) & 1) == 0 ? e : parent[e];
            }
            int c = LanternPosts.light(parent, price, reach, lighter);
            if (c != LanternPosts.INFEASIBLE && (best == LanternPosts.INFEASIBLE || c < best)) {
                best = c;
            }
        }
        return best;
    }
}
