// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.draw;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class SeedSackTest {

    private static final Hypergeometric H = new Hypergeometric(60, 18);

    @Test
    void pmfMatchesBinomialCoefficients() {
        assertThat(H.pmf(5, 2)).isCloseTo(0.32160324833123133, within(1e-12));
        double sum = 0;
        for (int k = 0; k <= 10; k++) {
            sum += H.pmf(10, k);
        }
        assertThat(sum).isCloseTo(1.0, within(1e-12));
        assertThat(H.pmf(5, 6)).isZero();
        assertThat(new Hypergeometric(10, 9).pmf(5, 3)).isZero();
        assertThat(H.mean(10)).isCloseTo(3.0, within(1e-12));
        assertThat(H.atLeast(0, 0)).isEqualTo(1.0);
        assertThat(Hypergeometric.logChoose(5, 7)).isInfinite();
        assertThat(H.total()).isEqualTo(60);
        assertThat(H.good()).isEqualTo(18);
    }

    @Test
    void smallestDrawForTheTerrace() {
        assertThat(H.smallestDraw(4, 0.90)).isEqualTo(19);
        assertThat(H.atLeast(19, 4)).isCloseTo(0.91117, within(1e-5));
        assertThat(H.atLeast(18, 4)).isLessThan(0.90);
        assertThat(new Hypergeometric(10, 2).smallestDraw(3, 0.5)).isEqualTo(-1);
        assertThat(H.smallestDraw(0, 1.0)).isZero();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new Hypergeometric(0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Hypergeometric(5, 6)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> H.pmf(61, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> H.smallestDraw(1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SeedSack.draw(5, 6, 1, new OddsRng(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> SeedSack.simulate(5, 2, 1, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        SeedSackQuest q = new SeedSackQuest();
        assertThatThrownBy(() -> q.plant(0, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void seededDrawsAgreeWithTheExactOdds() {
        double[] est = SeedSack.simulate(60, 18, 19, 4, 2026, 20_000);
        assertThat(est[0]).isCloseTo(H.atLeast(19, 4), within(0.01)).isBetween(est[1], est[2]);
        assertThat(SeedSack.simulate(60, 18, 19, 4, 2026, 20_000)).containsExactly(est);
        assertThat(SeedSack.draw(60, 18, 60, new OddsRng(3))).isEqualTo(18);
        assertThat(SeedSack.draw(60, 0, 30, new OddsRng(3))).isZero();
    }

    @Test
    void thriftyPlanterGetsTheNod() {
        SeedSackQuest q = new SeedSackQuest();
        assertThat(q.advised()).isEqualTo(19);
        assertThat(q.keeperLine()).contains("Plant 19").contains("91%");
        int greens = 0;
        for (long s = 0; s < 100; s++) {
            SeedSackQuest t = new SeedSackQuest();
            int sprouts = t.plant(19, s);
            assertThat(t.thrifty()).isTrue();
            assertThat(t.sprouted()).isEqualTo(sprouts);
            if (t.stage() == SeedSackQuest.Stage.TERRACE_GREEN) {
                greens++;
                assertThat(t.keeperLine()).contains("still holds next year");
            } else {
                assertThat(t.keeperLine()).contains("Only " + sprouts);
            }
        }
        assertThat(greens).isBetween(80, 99);
    }

    @Test
    void spendthriftAndGamblerGetWarned() {
        SeedSackQuest big = new SeedSackQuest();
        assertThat(big.chance(40)).isGreaterThan(big.chance(19));
        big.plant(60, 1);
        assertThat(big.stage()).isEqualTo(SeedSackQuest.Stage.TERRACE_GREEN);
        assertThat(big.keeperLine()).contains("next year's seed");
        assertThatThrownBy(() -> big.plant(5, 1)).isInstanceOf(IllegalStateException.class);
        boolean warned = false;
        for (long s = 0; s < 200 && !warned; s++) {
            SeedSackQuest small = new SeedSackQuest();
            if (small.plant(8, s) >= SeedSackQuest.NEEDED) {
                warned = small.keeperLine().contains("rolled the dice");
            }
        }
        assertThat(warned).isTrue();
    }
}
