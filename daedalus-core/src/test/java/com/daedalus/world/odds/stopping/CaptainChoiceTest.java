// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.stopping;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.OddsRng;
import java.util.Arrays;
import org.junit.jupiter.api.Test;

class CaptainChoiceTest {

    @Test
    void exactSuccessForTenCandidates() {
        assertThat(StoppingRule.success(10, 0)).isCloseTo(0.1, within(1e-12));
        assertThat(StoppingRule.bestCutoff(10)).isEqualTo(3);
        assertThat(StoppingRule.success(10, 3)).isCloseTo(0.3987, within(1e-4));
        assertThat(StoppingRule.success(1, 0)).isEqualTo(1.0);
        assertThat(StoppingRule.bestCutoff(3)).isEqualTo(1);
        assertThat(StoppingRule.success(3, 1)).isCloseTo(0.5, within(1e-12));
    }

    @Test
    void largeFieldsApproachOneOverE() {
        int r = StoppingRule.bestCutoff(200);
        assertThat(r / 200.0).isCloseTo(1 / Math.E, within(0.01));
        assertThat(StoppingRule.success(200, r)).isCloseTo(1 / Math.E, within(0.005));
    }

    @Test
    void ruleChoosesFirstToBeatTheLookPhase() {
        double[] s = {5, 2, 7, 3, 9, 1};
        assertThat(StoppingRule.choose(s, 2)).isEqualTo(2);
        assertThat(StoppingRule.choose(s, 3)).isEqualTo(4);
        assertThat(StoppingRule.choose(new double[] {9, 1, 2}, 1)).isEqualTo(2);
        assertThat(StoppingRule.choose(s, 0)).isZero();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> StoppingRule.success(5, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StoppingRule.success(0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> StoppingRule.choose(new double[0], 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CaptainLineup.shuffled(0, new OddsRng(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CaptainLineup.simulate(5, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void lineupIsASeededPermutation() {
        CaptainLineup a = CaptainLineup.shuffled(10, new OddsRng(4));
        CaptainLineup b = CaptainLineup.shuffled(10, new OddsRng(4));
        double[] seen = new double[10];
        for (int i = 0; i < 10; i++) {
            assertThat(a.score(i)).isEqualTo(b.score(i));
            seen[i] = a.score(i);
        }
        Arrays.sort(seen);
        assertThat(seen).containsExactly(1, 2, 3, 4, 5, 6, 7, 8, 9, 10);
        assertThat(a.score(a.best())).isEqualTo(10.0);
        assertThat(a.size()).isEqualTo(10);
    }

    @Test
    void seededLineupsAgreeWithTheExactChance() {
        double[] est = CaptainLineup.simulate(10, 3, 2026, 20_000);
        assertThat(StoppingRule.success(10, 3)).isBetween(est[1], est[2]);
        assertThat(CaptainLineup.simulate(10, 3, 2026, 20_000)).containsExactly(est);
    }

    @Test
    void questFollowsTheKeepersRule() {
        int best = 0;
        for (long seed = 0; seed < 100; seed++) {
            CaptainChoiceQuest q = new CaptainChoiceQuest(seed);
            assertThat(q.keeperLine()).contains("Send the first 3 away").contains("40%");
            for (int i = 0; i < 3; i++) {
                q.interview();
            }
            boolean hired = false;
            while (q.seen() < CaptainChoiceQuest.CANDIDATES) {
                if (q.interview()) {
                    q.hire();
                    hired = true;
                    break;
                }
            }
            if (!hired) {
                q.hire();
            }
            assertThat(q.hiredRank()).isBetween(1, 10);
            if (q.stage() == CaptainChoiceQuest.Stage.BEST_HIRED) {
                best++;
                assertThat(q.hiredRank()).isEqualTo(1);
                assertThat(q.keeperLine()).contains("best sailor");
            } else {
                assertThat(q.keeperLine()).contains("Number " + q.hiredRank());
            }
        }
        assertThat(best).isBetween(25, 55);
    }

    @Test
    void questGuardsItsOrder() {
        CaptainChoiceQuest q = new CaptainChoiceQuest(1);
        assertThat(q.hiredRank()).isEqualTo(-1);
        assertThatThrownBy(q::hire).isInstanceOf(IllegalStateException.class);
        assertThat(q.interview()).isTrue();
        for (int i = 1; i < CaptainChoiceQuest.CANDIDATES; i++) {
            q.interview();
        }
        assertThatThrownBy(q::interview).isInstanceOf(IllegalStateException.class);
        q.hire();
        assertThatThrownBy(q::interview).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(q::hire).isInstanceOf(IllegalStateException.class);
    }
}
