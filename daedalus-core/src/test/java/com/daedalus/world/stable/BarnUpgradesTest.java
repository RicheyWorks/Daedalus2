// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.stable.BarnUpgrades.Build;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BarnUpgradesTest {

    @Test
    void bestMatchesBruteForceOverEverySet() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = (int) (seed % 12);
            int[] v;
            int[] q;
            if (seed % 2 == 0) {
                int base = n / 3;
                v = BarnUpgrades.values(seed, n, base, 5, 12);
                q = BarnUpgrades.needs(seed, n, base, 50);
            } else {
                v = randomValues(seed, n);
                q = randomNeeds(seed, n);
            }
            Build b = BarnUpgrades.best(v, q);
            assertThat(b.coin()).as("seed %d", seed).isEqualTo(brute(v, q));
            assertThat(BarnUpgrades.closed(q, b.chosen())).isTrue();
            assertThat(BarnUpgrades.coin(v, b.chosen())).isEqualTo(b.coin());
            assertThat(BarnUpgrades.quest(v, q, b.chosen())).isTrue();
        }
    }

    @Test
    void oneAtATimeIsNeverBetterAndOftenWorse() {
        // 12 upgrades, 3 groundwork, gains 1-5, costs 1-12, 50% links: the habit earned less on 197 of
        // these 300 seeds when written.
        int worse = 0;
        for (long seed = 1; seed <= 300; seed++) {
            int[] v = BarnUpgrades.values(seed, 12, 3, 5, 12);
            int[] q = BarnUpgrades.needs(seed, 12, 3, 50);
            Build g = BarnUpgrades.oneAtATime(v, q);
            Build b = BarnUpgrades.best(v, q);
            assertThat(BarnUpgrades.closed(q, g.chosen())).isTrue();
            assertThat(g.coin()).isLessThanOrEqualTo(b.coin());
            if (g.coin() < b.coin()) {
                worse++;
            }
        }
        assertThat(worse).isGreaterThan(150);
    }

    @Test
    void sharedWiringOnlyPaysForTwo() {
        // Wiring costs 5; the hot-walker and the wash bay earn 3 each and both need the wiring.
        // Alone each loses 2, so the habit builds nothing. Together: 3 + 3 - 5 = 1.
        int[] v = {-5, 3, 3};
        int[] q = {0, 1, 1};
        assertThat(BarnUpgrades.oneAtATime(v, q)).isEqualTo(new Build(0, 0));
        assertThat(BarnUpgrades.best(v, q)).isEqualTo(new Build(1, 0b111));
        assertThat(BarnUpgrades.quest(v, q, 0)).isFalse();
    }

    @Test
    void openSetsFailTheQuest() {
        int[] v = {-5, 3, 3};
        int[] q = {0, 1, 1};
        assertThat(BarnUpgrades.closed(q, 0b110)).isFalse();
        assertThat(BarnUpgrades.quest(v, q, 0b110)).isFalse();
        assertThat(BarnUpgrades.quest(v, q, 0b1111)).isFalse();
        assertThat(BarnUpgrades.closure(q, 0b010)).isEqualTo(0b011);
        // Mutual prerequisites (a cycle) must be built together.
        int[] cv = {4, -3};
        int[] cq = {2, 1};
        assertThat(BarnUpgrades.best(cv, cq)).isEqualTo(new Build(1, 0b11));
        assertThat(BarnUpgrades.best(new int[0], new int[0]).coin()).isZero();
    }

    @Test
    void deterministicSeedsAndInputChecks() {
        assertThat(BarnUpgrades.values(5, 9, 3, 5, 12)).containsExactly(BarnUpgrades.values(5, 9, 3, 5, 12));
        assertThat(BarnUpgrades.needs(5, 9, 3, 50)).containsExactly(BarnUpgrades.needs(5, 9, 3, 50));
        assertThat(BarnUpgrades.QUEST_ID).isEqualTo("q_paying_barn");
        assertThatThrownBy(() -> BarnUpgrades.values(1, 31, 3, 5, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BarnUpgrades.best(new int[] {1}, new int[] {1})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BarnUpgrades.best(new int[] {1}, new int[] {2})).isInstanceOf(IllegalArgumentException.class);
    }

    private static long brute(int[] v, int[] q) {
        long best = 0;
        for (int mask = 0; mask < (1 << v.length); mask++) {
            if (BarnUpgrades.closed(q, mask)) {
                best = Math.max(best, BarnUpgrades.coin(v, mask));
            }
        }
        return best;
    }

    private static int[] randomValues(long seed, int n) {
        SplittableRandom rnd = new SplittableRandom(seed * 31);
        int[] v = new int[n];
        for (int i = 0; i < n; i++) {
            v[i] = rnd.nextInt(19) - 9;
        }
        return v;
    }

    private static int[] randomNeeds(long seed, int n) {
        SplittableRandom rnd = new SplittableRandom(seed * 37);
        int[] q = new int[n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                if (i != j && rnd.nextInt(100) < 15) {
                    q[i] |= 1 << j;
                }
            }
        }
        return q;
    }
}
