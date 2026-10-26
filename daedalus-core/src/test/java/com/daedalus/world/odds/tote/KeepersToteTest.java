// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tote;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

class KeepersToteTest {

    private static final double[] CUP = {0.5, 0.3, 0.2};

    private static ToteBoard board() {
        ToteBoard b = new ToteBoard(3, 0.10);
        b.bet(0, 60);
        b.bet(1, 30);
        b.bet(2, 10);
        return b;
    }

    @Test
    void toteOddsSplitThePoolAfterTakeout() {
        ToteBoard b = board();
        assertThat(b.pool()).isEqualTo(100);
        assertThat(b.odds(0)).isCloseTo(1.5, within(1e-12));
        assertThat(b.odds(2)).isCloseTo(9.0, within(1e-12));
        assertThat(b.oddsAfter(2, 10)).isCloseTo(4.95, within(1e-12));
        assertThat(b.oddsAfter(2, 0)).isEqualTo(b.odds(2));
        assertThat(b.payout(2, 3)).isEqualTo(27);
        assertThat(new ToteBoard(2, 0).odds(1)).isZero();
        assertThat(b.size()).isEqualTo(3);
        assertThat(b.takeout()).isEqualTo(0.10);
    }

    @Test
    void maxOverlayStakeMatchesBruteForce() {
        ToteBoard b = board();
        assertThat(b.maxOverlayStake(2, 0.2)).isEqualTo(9);
        for (double p : new double[] {0.12, 0.2, 0.33, 0.7}) {
            for (int i = 0; i < 3; i++) {
                long brute = 0;
                for (long s = 1; s < 10_000; s++) {
                    if (p * b.oddsAfter(i, s) > 1) {
                        brute = s;
                    }
                }
                assertThat(b.maxOverlayStake(i, p)).as("p=%s i=%s", p, i).isEqualTo(brute);
            }
        }
        assertThat(b.maxOverlayStake(2, 0.05)).isZero();
        assertThat(new ToteBoard(2, 0).maxOverlayStake(0, 1.0)).isEqualTo(Long.MAX_VALUE);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new ToteBoard(1, 0.1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ToteBoard(3, 0.3)).isInstanceOf(IllegalArgumentException.class);
        ToteBoard b = board();
        assertThatThrownBy(() -> b.bet(0, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.oddsAfter(0, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> b.maxOverlayStake(0, 1.2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrowdBets.fill(b, new double[] {0.5, 0.5}, 10, 1, 0.1, 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrowdBets.fill(b, CUP, 0, 1, 0.1, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CrowdBets.fill(b, new double[] {0, 0, 0}, 3, 1, 0.1, 1))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void crowdIsSeededAndFollowsTheChalk() {
        ToteBoard a = new ToteBoard(3, 0.15);
        ToteBoard b = new ToteBoard(3, 0.15);
        CrowdBets.fill(a, new double[] {0.6, 0.3, 0.1}, 400, 2, 0.5, 7);
        CrowdBets.fill(b, new double[] {0.6, 0.3, 0.1}, 400, 2, 0.5, 7);
        for (int i = 0; i < 3; i++) {
            assertThat(a.stakeOn(i)).isEqualTo(b.stakeOn(i));
        }
        assertThat(a.pool()).isEqualTo(800);
        assertThat(a.stakeOn(0)).isGreaterThan(a.stakeOn(1)).isGreaterThan(a.stakeOn(2));
    }

    @Test
    void keeperApprovesAnOverlayAndTheRaceSettlesIt() {
        ToteQuest found = null;
        for (long seed = 0; seed < 50; seed++) {
            ToteQuest t = new ToteQuest(CUP, seed);
            if (t.bestOverlay() >= 0) {
                found = t;
                break;
            }
        }
        assertThat(found).isNotNull();
        ToteQuest q = found;
        assertThat(q.pool()).isEqualTo((long) ToteQuest.CROWD * ToteQuest.CROWD_HERBS);
        assertThat(q.keeperLine()).contains("herbs in the pool");
        int best = q.bestOverlay();
        long max = q.maxOverlayStake(best);
        assertThat(max).isPositive();
        assertThat(q.odds(best)).isPositive();
        assertThat(q.back(best, Math.min(max, 5))).isTrue();
        assertThat(q.overlay()).isTrue();
        assertThat(q.keeperLine()).contains("An overlay");
        assertThatThrownBy(() -> q.back(0, 1)).isInstanceOf(IllegalStateException.class);
        long paid = q.race(11);
        assertThat(q.stage()).isIn(ToteQuest.Stage.WON, ToteQuest.Stage.LOST);
        assertThat(q.stage() == ToteQuest.Stage.WON).isEqualTo(q.winner() == best);
        assertThat(paid > 0).isEqualTo(q.stage() == ToteQuest.Stage.WON);
        assertThat(q.keeperLine()).containsAnyOf("Paid", "Not this heat");
    }

    @Test
    void floodingAnOutcomeIsUnderTheChalk() {
        ToteQuest q = new ToteQuest(CUP, 3);
        assertThatThrownBy(() -> q.race(1)).isInstanceOf(IllegalStateException.class);
        assertThat(q.back(2, 1_000)).isFalse();
        assertThat(q.keeperLine()).contains("Under the chalk");
        ToteQuest a = new ToteQuest(CUP, 3);
        a.back(2, 1_000);
        assertThat(a.race(5)).isEqualTo(q.race(5));
        assertThat(a.winner()).isEqualTo(q.winner());
    }

    @Test
    void backingRejectsUnknownOutcome() {
        ToteQuest q = new ToteQuest(CUP, 1);
        assertThatThrownBy(() -> q.back(3, 1)).isInstanceOf(IndexOutOfBoundsException.class);
    }
}
